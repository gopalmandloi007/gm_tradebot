# scripts/update_master.py
import requests, zipfile, io, os

MASTER_LINK = "https://app.definedgesecurities.com/public/allmaster.zip"
DEST_DIR = "data/master/"

def download_and_extract():
    os.makedirs(DEST_DIR, exist_ok=True)
    try:
        print("Downloading master file...")
        resp = requests.get(MASTER_LINK, stream=True, timeout=30)
        resp.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        z.extractall(DEST_DIR)
        return True, "✅ Master file updated successfully!"
    except Exception as e:
        return False, f"Failed to update master file: {e}"
        
