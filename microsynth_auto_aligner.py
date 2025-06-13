# Boiler plate stuff
import os
from dotenv import load_dotenv, find_dotenv
from benchling_sdk.benchling import Benchling
from benchling_sdk.auth.api_key_auth import ApiKeyAuth
import sys
import pandas as pd
from benchling_sdk.helpers.serialization_helpers import fields

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

# Pull the containers with the same name as the .gbk files

# Find the entities within these containers, and return the sequences

# Generate an alignment between the reference seuquences and the sequences from the gbk files

# Create new folder to hold the alignments generated

# Upload these alignments to Benchling in a specified folder

# Generate a result for the containers as TRUE if the alignment is 100% identical
## Maybe also include a score for this alignment?