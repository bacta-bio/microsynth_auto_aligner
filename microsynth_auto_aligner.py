# Boiler plate stuff
import os
from dotenv import load_dotenv, find_dotenv
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
import sys
import pandas as pd
from benchling_sdk.helpers.serialization_helpers import fields
from Bio import SeqIO
import requests
import json
import os

# initialize Benchling client
load_dotenv(find_dotenv())
DOMAIN  = os.getenv("BENCHLING_DOMAIN")
API_KEY = os.getenv("BENCHLING_API_KEY")

if API_KEY is None:
    sys.exit("Error: BENCHLING_API_KEY environment variable not set.")
if DOMAIN is None:
    sys.exit("Error: BENCHLING_DOMAIN environment variable not set.")

benchling  = Benchling(url=f"https://{DOMAIN}", auth_method=ApiKeyAuth(API_KEY))

sandbox_folder_id = "lib_70i3g6Il"

print("Benchling client initialised OK")

# Function to read the .gbk files from microsynth, pull the names of these files

def get_gbk_filenames_from_path(input_path: str) -> dict:
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

# Pull the containers with the same name as the .gbk files
def get_containers_by_name(benchling, names):
    found_containers = []
    for name in names:
        try:
            # Attempt to use the name filter if supported
            response = benchling.containers.list()
            for container_page in response:
                for container in container_page:
                    if container.name == name:
                        found_containers.append(container)
                        break
                else:
                    continue
                break
        except Exception as e:
            print(f"Error retrieving container {name}: {e}")
    return found_containers

# Find the entities within these containers, and return the sequences
def get_entities_from_containers(benchling, containers):
    entity_dict = {}
    for container in containers:
        try:
            contents = benchling.containers.list_contents(container_id=container.id)
            for item in contents:
                if hasattr(item, 'entity') and item.entity:
                    entity_dict[container.name] = item.entity
                    break  # Only take the first entity
        except Exception as e:
            print(f"Error retrieving sequences from container {container.name}: {e}")
    return entity_dict

def create_consensus_alignment_api(sequence_ids, domain, api_key, name=None, folder_id=None, test_mode=True):
    url = f"https://{domain}/api/v2/nucleotide-alignments:create-consensus-alignment"
    
    headers = {
        "Content-Type": "application/json"
    }
    auth_tuple = (api_key, '') 

    # --- Corrected Payload Structure for 'files' ---
    # Trying "entityId" as the key within the objects in the "files" array.
    payload = {
        "files": [{"entityId": seq_id} for seq_id in sequence_ids], # Changed "id" to "entityId"
        "algorithm": "MAFFT_AUTO"
    }
    if name:
        payload["name"] = name
    # folderId is not used for this endpoint based on previous errors.

    # --- Enhanced Debugging ---
    print("\n--- DEBUG: create_consensus_alignment_api ---")
    print(f"DEBUG: Request URL: {url}")
    print(f"DEBUG: Request Method: POST")
    print(f"DEBUG: Auth being used (Basic Auth): User='{auth_tuple[0]}', Password='{auth_tuple[1]}'")
    print(f"DEBUG: Request Payload: {json.dumps(payload, indent=2)}")
    if folder_id:
        print(f"DEBUG: folder_id '{folder_id}' was passed to the function but is NOT included in the request payload for this specific API endpoint.")
    # --- End Enhanced Debugging ---

    if test_mode:
        print("TEST MODE: Request would not be sent. Payload details above.")
        return None

    response = None
    try:
        # Using Basic Auth
        response = requests.post(url, auth=auth_tuple, headers=headers, json=payload)

        print(f"DEBUG: Response Status Code: {response.status_code}")
        if not response.ok:
            print(f"DEBUG: Response Headers: {response.headers}")
            print(f"DEBUG: Response Content (on error): {response.text}")
        
        response.raise_for_status() 
        
        alignment = response.json()
        print("Alignment created successfully. Full response:")
        print(json.dumps(alignment, indent=2))
        return alignment
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if response is not None:
            print(f"Failed to create alignment (HTTPError): {response.status_code} - {response.text}")
        else:
            print(f"Failed to create alignment (HTTPError): No response object.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if response is not None:
            print(f"Response status at time of error: {response.status_code}")
            print(f"Response text at time of error: {response.text}")
        return None

def main ():
    get_gbk_filenames_from_path("/Users/maximusmay/Developer/microsynth_auto_aligner/data/microsynth_data_example")
    fasta_dict = get_gbk_filenames_from_path("/Users/maximusmay/Developer/microsynth_auto_aligner/data/microsynth_data_example")
    container_names = list(fasta_dict.keys())

    # Debugging 
    print(f"\nFound {len(fasta_dict)} .fasta files.")
    for name, path in fasta_dict.items():
        print(f"{name}: {path}")

    get_containers_by_name(benchling, container_names)
    found_containers = get_containers_by_name(benchling, container_names)
    entity_dict = get_entities_from_containers(benchling, found_containers)

    # Debugging
    print(f"\nFound {len(found_containers)} containers with matching names.")
    print("Containers retrieved:")
    for container in found_containers:
        print(f"Container ID: {container.id}, Name: {container.name}")

    get_entities_from_containers(benchling, found_containers)
    sequence_ids = [entity.id for entity in entity_dict.values()]

    # Debugging
    print(f"\nFound {len(sequence_ids)} sequences in the containers.")
    for entity in entity_dict.values():
        print(f"Entity ID: {entity.id}, Name: {entity.name}, Bases (first 30): {entity.bases[:30]}")

    create_consensus_alignment_api(sequence_ids, DOMAIN, API_KEY, name="Microsynth Auto Alignment", folder_id=sandbox_folder_id, test_mode=False)
    # create_benchling_consensus_alignment(benchling, entity_dict)

if __name__ == "__main__":
    main()

# # Function to create a consensus alignment in Benchling using the entities found
# def create_benchling_consensus_alignment(benchling, entity_dict, alignment_name="Microsynth Auto Alignment"):
#     sequence_ids = [entity.id for entity in entity_dict.values()]
#     if not sequence_ids:
#         print("No sequence IDs available for alignment.")
#         return None

#     try:
#         alignment = benchling.nucleotide_alignments.create_consensus_alignment(
#             sequence_ids=sequence_ids,
#             alignment_method="MAFFT_AUTO"
#         )
#         print(f"Consensus alignment created with ID: {alignment.id}")
#         return alignment
#     except Exception as e:
#         print(f"Failed to create alignment: {e}")
#         return None


# # Example call to create the alignment
# alignment = create_benchling_consensus_alignment(benchling, entity_dict)


# Generate an alignment between the reference seuquences and the sequences from the gbk files
# def generate_alignments(entity_dict, gbk_dict):
#     alignments = {}
#     for container_id, entity in entity_dict.items():
#         tube_name = container_id  # Now matching container ID to gbk_dict key
#         print(f"Processing entity from container: {tube_name}")
#         if tube_name in gbk_dict:
#             print(f"Match found in gbk_dict for: {tube_name}")
#             gbk_file_path = gbk_dict[tube_name]
#             with open(gbk_file_path, "r") as file:
#                 record = next(SeqIO.parse(file, "genbank"))
#                 reference_sequence = str(record.seq)
#             print(f"Entity sequence (first 30 bp): {entity.bases[:30]}")
#             print(f"Reference sequence (first 30 bp): {reference_sequence[:30]}")
#             is_identical = entity.bases == reference_sequence
#             print(f"Is identical: {is_identical}")
#             alignment_result = {
#                 "tube_name": tube_name,
#                 "entity_id": entity.id,
#                 "alignment_score": 100 if is_identical else 0,
#                 "is_identical": is_identical
#             }
#             alignments[tube_name] = alignment_result
#         else:
#             print(f"No match found in gbk_dict for: {tube_name}")
#     return alignments
# alignments = generate_alignments(entity_dict, fasta_dict)
# print("\nGenerated alignments:")
# print(f"Alignments generated: {len(alignments)}")  # Just before the final print loop

# for tube_name, result in alignments.items():
#     print(f"{tube_name}: Alignment Score: {result['alignment_score']}, Is Identical: {result['is_identical']}")

# Create new folder to hold the alignments generated

# Upload these alignments to Benchling in a specified folder

# Generate a result for the containers as TRUE if the alignment is 100% identical
## Maybe also include a score for this alignment?