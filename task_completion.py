import time
import requests
import json
import os
from dotenv import load_dotenv, find_dotenv

# initialize Benchling client
load_dotenv(find_dotenv())
DOMAIN  = os.getenv("BENCHLING_DOMAIN")
API_KEY = os.getenv("BENCHLING_API_KEY")

# Fill this in yourself
TASK_ID = "1c1a1364-c31a-410f-9cc4-922c5e4c1394"

auth = (API_KEY, "")
url = f"https://{DOMAIN}/api/v2/tasks/{TASK_ID}"

# Poll until the task is no longer running
while True:
    resp = requests.get(url, auth=auth) # type: ignore
    resp.raise_for_status()
    task = resp.json()
    status = task["status"]
    print(f"Task {TASK_ID} is {status}")
    if status not in ("QUEUED", "IN_PROGRESS"):
        break
    time.sleep(5)

if status == "COMPLETED":
    # The result block contains the new alignment’s ID
    alignment_id = task["result"]["id"]
    print("✅ Alignment created! ID =", alignment_id)
    print("View it at:")
    print(f"https://{DOMAIN}/#/alignment/{alignment_id}")
else:
    # Print detailed error information for failed tasks
    print(f"⚠️ Task {TASK_ID} finished with status {status}")
    # Output the entire task JSON for debugging
    print("Full task payload:", json.dumps(task, indent=2))