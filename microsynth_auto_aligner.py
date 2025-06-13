# Boiler plate stuff
import os
from dotenv import load_dotenv, find_dotenv
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
import sys
import pandas as pd
from benchling_sdk.helpers.serialization_helpers import fields
from Bio import SeqIO
import json
import requests

# initialize Benchling client
load_dotenv(find_dotenv())
DOMAIN  = os.getenv("BENCHLING_DOMAIN")
API_KEY = os.getenv("BENCHLING_API_KEY")

if API_KEY is None:
    sys.exit("Error: BENCHLING_API_KEY environment variable not set.")
if DOMAIN is None:
    sys.exit("Error: BENCHLING_DOMAIN environment variable not set.")

benchling  = Benchling(url=f"https://{DOMAIN}", auth_method=ApiKeyAuth(API_KEY))

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

fasta_dict = get_gbk_filenames_from_path("/Users/maximusmay/Developer/microsynth_auto_aligner/data/microsynth_data_example")
print(f"\nFound {len(fasta_dict)} .fasta files.")
for name, path in fasta_dict.items():
    print(f"{name}: {path}")

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

container_names = list(fasta_dict.keys())
found_containers = get_containers_by_name(benchling, container_names)


# Debugging
print(f"\nFound {len(found_containers)} containers with matching names.")
print("Containers retrieved:")
for container in found_containers:
    print(f"Container ID: {container.id}, Name: {container.name}")


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


entity_dict = get_entities_from_containers(benchling, found_containers)
print(f"\nFound {len(entity_dict)} entities in the containers.")
print("Entities retrieved:")
for container in found_containers:
    entity = entity_dict.get(container.id)
    if entity:
        print(f"Entity ID: {entity.id}, Name: {entity.name}, Sequence: {entity.bases[:30]}...")  # Print first 30 characters of sequence for brevity


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

def create_consensus_alignment_api(sequence_ids, domain, api_key, name=None, folder_id=None, test_mode=True):
    url = f"https://{domain}/api/v2/nucleotide-alignments:create-consensus-alignment"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "sequenceIds": sequence_ids,
        "alignmentMethod": "MAFFT_AUTO"
    }
    if name:
        payload["name"] = name
    if folder_id:
        payload["folderId"] = folder_id

    if test_mode:
        print("TEST MODE: Here's what would be sent to Benchling:")
        print(json.dumps(payload, indent=2))
        return None

    response = requests.post(url, headers=headers, json=payload)
    if response.ok:
        alignment = response.json()
        print("Alignment created successfully. Full response:")
        print(json.dumps(alignment, indent=2))
        return alignment
    else:
        print(f"Failed to create alignment: {response.status_code} - {response.text}")
        return None

# Example usage:
sequence_ids = [entity.id for entity in entity_dict.values()]
sandbox_folder_id = "lib_70i3g6Il"
create_consensus_alignment_api(sequence_ids, DOMAIN, API_KEY, name="Microsynth Auto Alignment", folder_id=sandbox_folder_id, test_mode=False)
