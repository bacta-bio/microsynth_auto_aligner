# Boiler plate stuff
import argparse
import base64
import os
import sys
from typing import Callable, Optional

import pandas as pd
import requests
from Bio import SeqIO
from dotenv import find_dotenv, load_dotenv

# Import our custom Benchling client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchling import BenchlingClient, get_config

# Initialize Benchling client
load_dotenv(find_dotenv())
try:
    benchling_client = BenchlingClient()
except Exception as e:
    sys.exit(f"Error initializing Benchling client: {e}")

LOG_FUNCTION: Callable[[str], None] = print


def set_log_function(func: Callable[[str], None]) -> None:
    """Allow callers to override how messages are surfaced."""
    global LOG_FUNCTION
    LOG_FUNCTION = func


def log(message: str) -> None:
    LOG_FUNCTION(message)


def find_container(identifier: str):
    """Find a container by name, display ID, or barcode using the Benchling API."""
    # Search strategies for finding containers
    search_strategies = [
        ("name", {"name": identifier}),
        ("display ID", {"displayIds": [identifier]}),
        ("barcode", {"barcodes": [identifier]}),
    ]

    for label, params in search_strategies:
        try:
            response = benchling_client.make_request('GET', '/containers', params=params)
            containers = response.json().get('containers', [])
            
            if not containers:
                continue
                
            container = containers[0]  # Take the first match
            
            # Extract container attributes safely
            container_name = container.get('name')
            container_barcode = container.get('barcode')
            container_display_id = container.get('displayId')

            # Verify the match is correct
            if (
                container_name == identifier
                or container_barcode == identifier
                or container_display_id == identifier
                or label in {"barcode", "display ID"}
            ):
                if label == "barcode" and container_name != identifier:
                    log(
                        f"Info: Matched {identifier} by barcode. Container name is {container_name} and barcode {container_barcode}."
                    )
                elif label == "display ID" and container_display_id != identifier:
                    log(
                        f"Info: Matched {identifier} by display ID. Container name is {container_name} and display ID {container_display_id}."
                    )
                return container
                
        except Exception as exc:
            log(f"Error retrieving container {identifier} by {label}: {exc}")
            continue

    return None

# Function to read the .gbk files from microsynth, pull the names of these files
def get_fasta_filenames(input_path: str) -> dict:
    fasta_dict = {}
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if file.lower().endswith(".fasta"):
                full_path = os.path.join(root, file)
                tube_name = file.replace(".fasta", "")
                if tube_name in fasta_dict:
                    log(f"Warning: Duplicate tube name found: {tube_name}")
                fasta_dict[tube_name] = full_path
    return fasta_dict

def create_file_payload_df(fasta_dict):
    rows = []
    for tube_name, fasta_path in fasta_dict.items():
        # Read sequence from FASTA
        try:
            record = SeqIO.read(fasta_path, "fasta")
        except Exception as e:
            log(f"Error reading FASTA {fasta_path}: {e}")
            continue

        # Find the matching container on Benchling
        container = find_container(tube_name)
        if not container:
            log(f"Warning: No container found for {tube_name}")
            continue

        # Get the first entity inside that container
        try:
            response = benchling_client.make_request('GET', f'/containers/{container["id"]}/contents')
            contents = response.json().get('contents', [])
            entity = None
            
            # Find the first entity in the container contents
            for item in contents:
                if item.get('entity'):
                    entity = item['entity']
                    break
                    
        except Exception as e:
            log(f"Error retrieving sequences from container {tube_name}: {e}")
            continue

        if not entity:
            log(f"Warning: No entity found in container {tube_name}")
            continue

        # Collect row for DataFrame
        rows.append({
            "tube_name": tube_name,
            "template_id": entity["id"],
            "fasta_sequence": str(record.seq),
            "fasta_path": fasta_path,
        })
    return pd.DataFrame(rows)

def create_template_alignment_api(file_payload):
    """Create template alignments using the Benchling API."""
    config = get_config()
    alignment_results = []
    
    for _, row in file_payload.iterrows():
        # Read the FASTA file as binary and base64-encode it
        with open(row["fasta_path"], "rb") as fasta_file:
            raw_bytes = fasta_file.read()
        encoded_file = base64.b64encode(raw_bytes).decode("ascii")
        
        payload = {
            "algorithm": "mafft",
            "clustaloOptions": {
                "maxGuidetreeIterations": -1,
                "maxHmmIterations": -1,
                "mbedGuideTree": True,
                "mbedIteration": True,
                "numCombinedIterations": 0
            },
            "mafftOptions": {
                "adjustDirection": "fast",
                "gapExtensionPenalty": 0,
                "gapOpenPenalty": 1.53,
                "maxIterations": 0,
                "retree": 2,
                "strategy": "auto"
            },
            "templateSequenceId": row["template_id"],
            "files": [
                {
                    "data": encoded_file,
                    "name": f"{row['tube_name']}.fasta"
                }
            ],
            "name": row["tube_name"]
        }
        
        try:
            response = benchling_client.make_request(
                'POST', 
                '/nucleotide-alignments:create-template-alignment', 
                data=payload
            )
            response_data = response.json()
            print(f"DEBUG: Response data for {row['tube_name']}: {response_data}")  # Console log
            
            # Check for both 'id' and 'taskId' fields
            alignment_id = response_data.get('id') or response_data.get('taskId')
            alignment_name = response_data.get('name', row['tube_name'])
            
            log(f"Template alignment created for {row['tube_name']}: {response_data}")
            
            # Store the result for returning to the caller
            alignment_results.append({
                'tube_name': row['tube_name'],
                'alignment_id': alignment_id,
                'alignment_name': alignment_name,
                'success': True,
                'response_data': response_data  # Include full response for debugging
            })
            
        except Exception as e:
            print(f"DEBUG: Error for {row['tube_name']}: {e}")  # Console log
            log(f"Error creating alignment for {row['tube_name']}: {e}")
            alignment_results.append({
                'tube_name': row['tube_name'],
                'alignment_id': None,
                'alignment_name': row['tube_name'],
                'success': False,
                'error': str(e)
            })
    
    return alignment_results


def run_alignment(file_path: str) -> tuple[bool, list]:
    """Run alignment process and return success status and alignment results."""
    log("\nworking...")
    fasta_dict = get_fasta_filenames(file_path)
    file_df = create_file_payload_df(fasta_dict)
    if file_df.empty:
        log(
            "\nNo containers with matching names or barcodes were found. "
            "Verify that your FASTA filenames match the Benchling container identifiers."
        )
        return False, []
    
    alignment_results = create_template_alignment_api(file_df)
    successful_alignments = [r for r in alignment_results if r['success']]
    
    log(f"\nSuccessfully created template alignments for {len(successful_alignments)} tubes. Results uploaded to Benchling.")
    return len(successful_alignments) > 0, alignment_results


def launch_gui() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ImportError as exc:  # pragma: no cover - Tkinter may be missing on headless systems
        log(f"Error: Unable to launch GUI because tkinter is unavailable: {exc}")
        sys.exit(1)

    class MicrosynthAlignerGUI:
        def __init__(self) -> None:
            self.root = tk.Tk()
            self.root.title("Microsynth Auto Aligner")
            self.path_var = tk.StringVar()

            tk.Label(self.root, text="Microsynth data folder:", anchor="w").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
            entry = tk.Entry(self.root, textvariable=self.path_var, width=50)
            entry.grid(row=1, column=0, padx=10, pady=5, sticky="we")
            entry.focus()

            tk.Button(self.root, text="Browse…", command=self.browse).grid(row=1, column=1, padx=10, pady=5)

            self.run_button = tk.Button(self.root, text="Run Alignment", command=self.start_alignment)
            self.run_button.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="we")

            self.log_text = tk.Text(self.root, height=15, width=80, state="disabled")
            self.log_text.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

            self.root.grid_rowconfigure(3, weight=1)
            self.root.grid_columnconfigure(0, weight=1)

        def browse(self) -> None:
            selected = filedialog.askdirectory(title="Select Microsynth Folder")
            if selected:
                self.path_var.set(selected)

        def append_log(self, message: str) -> None:
            def update() -> None:
                self.log_text.configure(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            self.root.after(0, update)

        def start_alignment(self) -> None:
            path = self.path_var.get().strip()
            if not path:
                messagebox.showwarning("Microsynth Auto Aligner", "Please choose a folder containing Microsynth FASTA files.")
                return
            self.run_button.config(state="disabled")

            def worker() -> None:
                previous_logger = LOG_FUNCTION

                def gui_log(msg: str) -> None:
                    self.append_log(msg)

                set_log_function(gui_log)
                try:
                    success = run_alignment(path)
                    if success:
                        message = "Template alignments created successfully."
                        self.root.after(0, lambda: messagebox.showinfo("Microsynth Auto Aligner", message))
                    else:
                        message = "No alignments were created. Check the log for details."
                        self.root.after(0, lambda: messagebox.showwarning("Microsynth Auto Aligner", message))
                except Exception as exc:
                    self.append_log(f"Unexpected error: {exc}")
                    self.root.after(0, lambda: messagebox.showerror("Microsynth Auto Aligner", f"Unexpected error: {exc}"))
                finally:
                    set_log_function(previous_logger)
                    self.root.after(0, lambda: self.run_button.config(state="normal"))

            import threading

            threading.Thread(target=worker, daemon=True).start()

        def start(self) -> None:
            self.root.mainloop()

    gui = MicrosynthAlignerGUI()
    gui.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Microsynth Auto Aligner")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface.")
    parser.add_argument("--path", type=str, help="Path to Microsynth data directory.")
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    if args.path:
        success = run_alignment(args.path)
        if success:
            print("\nAlignment completed successfully!")
            while True:
                again = input("\nWould you like to run another alignment? (yes/no): ").strip().lower()
                if again in ('no', 'n'):
                    break
                elif again in ('yes', 'y'):
                    file_path = input("\nPaste your path for the microsynth data: ")
                    run_alignment(file_path)
                else:
                    print("Please answer 'yes' or 'no'")
        return

    # Interactive loop
    while True:
        file_path = input("\nPaste your path for the microsynth data (or 'exit' to quit): ").strip()
        if file_path.lower() in ('exit', 'quit', 'q'):
            print("Goodbye!")
            break
        
        if not file_path:
            print("Please provide a valid path or type 'exit' to quit.")
            continue
            
        success = run_alignment(file_path)
        if success:
            print("\nAlignment completed successfully!")
            again = input("\nWould you like to run another alignment? (yes/no): ").strip().lower()
            if again in ('no', 'n'):
                print("Goodbye!")
                break
            # If yes, the loop continues

if __name__ == "__main__":
    main()
