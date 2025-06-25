# Boiler plate stuff
import os
from dotenv import load_dotenv, find_dotenv
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
import sys
import pandas as pd
from Bio import SeqIO
import requests
import base64

# initialize Benchling client
load_dotenv(find_dotenv())
DOMAIN  = os.getenv("BENCHLING_DOMAIN")
API_KEY = os.getenv("BENCHLING_API_KEY")

if API_KEY is None:
    sys.exit("Error: BENCHLING_API_KEY environment variable not set.")
if DOMAIN is None:
    sys.exit("Error: BENCHLING_DOMAIN environment variable not set.")

benchling  = Benchling(url=f"https://{DOMAIN}", auth_method=ApiKeyAuth(API_KEY))

# Function to read the .gbk files from microsynth, pull the names of these files
def get_fasta_filenames(input_path: str) -> dict:
    fasta_dict = {}
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if file.lower().endswith(".fasta"):
                full_path = os.path.join(root, file)
                tube_name = file.replace(".fasta", "")
                if tube_name in fasta_dict:
                    print(f"Warning: Duplicate tube name found: {tube_name}")
                fasta_dict[tube_name] = full_path
    return fasta_dict

def create_file_payload_dict(fasta_dict):
    rows = []
    for tube_name, fasta_path in fasta_dict.items():
        # Read sequence from FASTA
        try:
            record = SeqIO.read(fasta_path, "fasta")
        except Exception as e:
            print(f"Error reading FASTA {fasta_path}: {e}")
            continue

        # Find the matching container on Benchling
        try:
            pages = benchling.containers.list(name=tube_name)
            container = next((c for page in pages for c in page if c.name == tube_name), None)
        except Exception as e:
            print(f"Error retrieving container {tube_name}: {e}")
            continue

        if not container:
            print(f"Warning: No container found for {tube_name}")
            continue

        # Get the first entity inside that container
        try:
            contents = benchling.containers.list_contents(container_id=container.id)
            entity = next((item.entity for item in contents if hasattr(item, 'entity') and item.entity), None)
        except Exception as e:
            print(f"Error retrieving sequences from container {tube_name}: {e}")
            continue

        if not entity:
            print(f"Warning: No entity found in container {tube_name}")
            continue

        # Collect row for DataFrame
        rows.append({
            "tube_name": tube_name,
            "sequence_id": entity.id, # type: ignore
            "fasta_sequence": str(record.seq),
            "fasta_path": fasta_path,
        })
    return pd.DataFrame(rows)

def create_template_alignment_api(file_payload, domain, api_key, folder_id=None,):
    url = f"https://{domain}/api/v2/nucleotide-alignments:create-template-alignment"
    headers = {"Content-Type": "application/json"}
    auth_tuple = (api_key, "")
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
            "templateSequenceId": row["sequence_id"],
            "files": [
                {
                    "data": encoded_file,
                    "name": f"{row['tube_name']}.fasta"
                }
            ],
            "name": row["tube_name"]
        }
        try:
            response = requests.post(url, auth=auth_tuple, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Template alignment created for {row['tube_name']}: {response.json()}")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error creating alignment for {row['tube_name']}: {http_err} - {response.text}") # type: ignore
        except Exception as e:
            print(f"Error creating alignment for {row['tube_name']}: {e}")

def main ():
    file_path = input("Paste your path for the microsynth data: ")
    fasta_dict = get_fasta_filenames(file_path)
    file_payload = create_file_payload_dict(fasta_dict)
    create_template_alignment_api(file_payload, DOMAIN, API_KEY)

if __name__ == "__main__":
    main()