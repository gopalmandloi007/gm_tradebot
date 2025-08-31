# scripts/update_master.py
import requests
import zipfile
import os
import io

# --- Constants ---
BASE_FILES = "https://app.definedgesecurities.com/public"
MASTER_ZIP_NAME = "nsecash.zip"  # Change if you want BSE/NFO/MCX etc.
SAVE_DIR = "data/master"          # Folder where CSV will be saved

def download_master():
    """
    Downloads the master zip file from Definedge and extracts it to SAVE_DIR.
    """
    try:
        # --- Ensure folder exists ---
        os.makedirs(SAVE_DIR, exist_ok=True)

        # --- Download zip file ---
        url = f"{BASE_FILES}/{MASTER_ZIP_NAME}"
        print(f"Downloading {url} ...")
        r = requests.get(url, stream=True, timeout=25)
        r.raise_for_status()

        # --- Read zip in memory ---
        z = zipfile.ZipFile(io.BytesIO(r.content))

        # --- Extract all files into SAVE_DIR ---
        z.extractall(SAVE_DIR)

        print(f"✅ Master file updated successfully! Saved in {SAVE_DIR}/")
        return True
    except Exception as e:
        print(f"❌ Failed to update master file: {e}")
        return False
        
