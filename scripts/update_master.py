# scripts/update_master.py
import os
import zipfile
import requests
from definedge_api import DefinedgeClient

MASTER_DIR = "data/master"
MASTER_FILES = {
    "NSE Cash": "nsecash.zip",
    "NSE FNO": "nsefno.zip",
    "BSE Cash": "bsecash.zip",
    "BSE FNO": "bsefno.zip",
    "MCX FNO": "mcxfno.zip",
    "All Segments": "allmaster.zip"
}
MASTER_BASE_URL = "https://app.definedgesecurities.com/public"

def ensure_master_dir():
    if not os.path.exists(MASTER_DIR):
        os.makedirs(MASTER_DIR)
    return MASTER_DIR

def download_master(file_key="All Segments"):
    """
    Download master zip and extract CSV into data/master/
    """
    if file_key not in MASTER_FILES:
        raise ValueError(f"Invalid master file key: {file_key}")
    zip_name = MASTER_FILES[file_key]
    dest_dir = ensure_master_dir()
    dest_path = os.path.join(dest_dir, zip_name)

    url = f"{MASTER_BASE_URL}/{zip_name}"
    print(f"Downloading {zip_name} from Definedge...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024*32):
            f.write(chunk)
    print(f"Downloaded to {dest_path}")

    # Extract zip
    print("Extracting CSV...")
    with zipfile.ZipFile(dest_path, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)
    print(f"Extracted to {dest_dir}")

    # Optionally, delete zip after extraction
    # os.remove(dest_path)
    print("Master file update complete!")

if __name__ == "__main__":
    download_master("All Segments")
