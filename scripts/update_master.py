# script/update_master.py
import os
import zipfile
import io
import pandas as pd
from definedge_api import DefinedgeClient

# ---- Configuration ----
MASTER_FOLDER = "data/master/"
MASTER_FILES = {
    "NSE_CASH": "nsecash.zip",
    "NSE_FNO": "nsefno.zip",
    "BSE_CASH": "bsecash.zip",
    "BSE_FNO": "bsefno.zip",
    "MCX_FNO": "mcxfno.zip",
    "ALL": "allmaster.zip"
}

# Ensure folder exists
os.makedirs(MASTER_FOLDER, exist_ok=True)

def download_and_extract(client: DefinedgeClient, file_key: str = "ALL"):
    try:
        zip_name = MASTER_FILES[file_key]
        dest_zip_path = os.path.join(MASTER_FOLDER, zip_name)
        
        print(f"Downloading {zip_name} ...")
        client.download_master_zip(zip_name, dest_zip_path)
        print(f"✅ Downloaded: {dest_zip_path}")

        # Extract zip
        with zipfile.ZipFile(dest_zip_path, "r") as zip_ref:
            zip_ref.extractall(MASTER_FOLDER)
        print(f"✅ Extracted master files to: {MASTER_FOLDER}")

        # Optional: list extracted files
        extracted_files = os.listdir(MASTER_FOLDER)
        print("Extracted files:", extracted_files)

    except Exception as e:
        print("❌ Failed to download/update master file:", e)

if __name__ == "__main__":
    client = DefinedgeClient()
    # Make sure session key is set if required
    # client.set_session_key("YOUR_API_SESSION_KEY")
    
    download_and_extract(client)
    
