import os
import json

PERSISTENT_STORAGE_PATH = "/data"
DIFF_STORE_PATH = os.path.join(PERSISTENT_STORAGE_PATH, "diff_store")
os.makedirs(DIFF_STORE_PATH, exist_ok=True)

def save_to_diff_store(user_id, data):
    path = os.path.join(DIFF_STORE_PATH, f"{user_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def load_from_diff_store(user_id):
    path = os.path.join(DIFF_STORE_PATH, f"{user_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None
