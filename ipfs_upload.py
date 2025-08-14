import requests
import os
from dotenv import load_dotenv
import json
import logging
import time

# Setup logging
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

def upload_image_to_ipfs(image_path: str) -> str:
    api_key = os.getenv("PINATA_API_KEY")
    secret_key = os.getenv("PINATA_SECRET_API_KEY")
    if not api_key or not secret_key:
        logging.error("PINATA_API_KEY or PINATA_SECRET_API_KEY not set in .env")
        raise ValueError("PINATA_API_KEY or PINATA_SECRET_API_KEY not set in .env")

    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        raise FileNotFoundError(f"Image file not found: {image_path}")

    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": secret_key
    }
    with open(image_path, "rb") as file:
        files = {"file": (os.path.basename(image_path), file, "image/png")}
        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            ipfs_hash = response.json().get("IpfsHash")
            if not ipfs_hash:
                logging.error("Failed to get IPFS hash for image")
                raise ValueError("Failed to get IPFS hash for image")
            ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
            logging.info(f"Image uploaded to IPFS: {ipfs_url}")
            time.sleep(5)  # Wait for IPFS availability
            response = requests.head(ipfs_url, timeout=10)
            if response.status_code != 200:
                logging.error(f"Image URL {ipfs_url} is not accessible: {response.status_code}")
                raise ValueError(f"Image URL {ipfs_url} is not accessible: {response.status_code}")
            return ipfs_url
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading image to IPFS: {str(e)}", exc_info=True)
            raise

def upload_metadata_to_ipfs(name: str, description: str, image_ipfs: str, attributes: list) -> str:
    api_key = os.getenv("PINATA_API_KEY")
    secret_key = os.getenv("PINATA_SECRET_API_KEY")
    if not api_key or not secret_key:
        logging.error("PINATA_API_KEY or PINATA_SECRET_API_KEY not set in .env")
        raise ValueError("PINATA_API_KEY or PINATA_SECRET_API_KEY not set in .env")

    metadata = {
        "name": name,
        "description": description,
        "image": image_ipfs,
        "attributes": attributes
    }
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": secret_key,
        "Content-Type": "application/json"
    }
    payload = {"pinataContent": metadata}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        ipfs_hash = response.json().get("IpfsHash")
        if not ipfs_hash:
            logging.error("Failed to get IPFS hash for metadata")
            raise ValueError("Failed to get IPFS hash for metadata")
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        logging.info(f"Metadata uploaded to IPFS: {ipfs_url}")
        time.sleep(5)  # Wait for IPFS availability
        response = requests.get(ipfs_url, timeout=10)
        if response.status_code != 200:
            logging.error(f"Metadata URL {ipfs_url} is not accessible: {response.status_code}")
            raise ValueError(f"Metadata URL {ipfs_url} is not accessible: {response.status_code}")
        return ipfs_url
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading metadata to IPFS: {str(e)}", exc_info=True)
        raise