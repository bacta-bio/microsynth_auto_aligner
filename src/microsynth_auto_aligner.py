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
            # Don't log the error here - just continue to try next search strategy
            continue

    return None

# Function to read FASTA files from microsynth, pull the names of these files
def get_fasta_filenames(input_path: str) -> dict:
    """Scan input folder for FASTA files (.fasta, .fa) only.
    
    Note: We only extract FASTA files to avoid duplicates if both .fasta and .gbk files exist.
    
    Returns a dictionary mapping tube_name (filename without extension) to full file path.
    """
    fasta_dict = {}
    supported_extensions = (".fasta", ".fa")
    
    for root, dirs, files in os.walk(input_path):
        for file in files:
            file_lower = file.lower()
            # Check if file has a FASTA extension (not .gbk/.genbank to avoid duplicates)
            if any(file_lower.endswith(ext) for ext in supported_extensions):
                full_path = os.path.join(root, file)
                # Extract tube name by removing FASTA extensions
                tube_name = file
                for ext in supported_extensions:
                    if tube_name.lower().endswith(ext):
                        tube_name = tube_name[:-len(ext)]
                        break
                
                if tube_name in fasta_dict:
                    log(f"Warning: Duplicate tube name found: {tube_name}")
                fasta_dict[tube_name] = full_path
    return fasta_dict

def create_file_payload_df(fasta_dict):
    rows = []
    for tube_name, fasta_path in fasta_dict.items():
        # Read sequence from file (supports FASTA and GenBank formats)
        try:
            # Determine file format from extension
            file_ext = os.path.splitext(fasta_path)[1].lower()
            if file_ext in ('.gbk', '.genbank'):
                record = SeqIO.read(fasta_path, "genbank")
            else:
                record = SeqIO.read(fasta_path, "fasta")
        except Exception as e:
            log(f"Error reading sequence file {fasta_path}: {e}")
            continue

        # Find the matching container on Benchling
        container = find_container(tube_name)
        if not container:
            log(f"Warning: No container found for {tube_name}")
            continue

        # Get the first entity inside that container
        entity_id = None
        sequence_web_url = None
        try:
            response = benchling_client.make_request('GET', f'/containers/{container["id"]}/contents')
            contents = response.json().get('contents', [])
            
            # Get the first entity from contents
            if contents and contents[0].get('entity'):
                entity = contents[0]['entity']
                entity_id = entity.get('id')
                sequence_web_url = entity.get('webURL')
                    
        except Exception as e:
            log(f"Warning: Error retrieving sequences from container {tube_name}: {e}")
            continue

        if not entity_id:
            log(f"Warning: No entity found in container {tube_name}")
            continue

        # Collect row for DataFrame
        rows.append({
            "tube_name": tube_name,
            "template_id": entity_id,  # Entity ID for template alignment API
            "sequence_web_url": sequence_web_url,  # Web URL directly from entity
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
                'sequence_url': row.get('sequence_web_url'),  # Web URL directly from entity
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
                'sequence_url': row.get('sequence_web_url'),  # Web URL even on error
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