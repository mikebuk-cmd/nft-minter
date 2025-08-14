import requests
import os
from dotenv import load_dotenv
import time
import logging

# Setup logging
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

def mint_nft(address: str, image_ipfs: str, metadata_ipfs: str, name: str, description: str, attributes: list) -> dict:
    # Get environment variables
    api_host = os.getenv("GETGEMS_API_HOST", "api.testnet.getgems.io")
    auth_token = os.getenv("GETGEMS_AUTH_TOKEN")
    collection_address = os.getenv("COLLECTION_ADDRESS")

    # Check for required environment variables
    if not auth_token:
        logging.error("GETGEMS_AUTH_TOKEN not set in .env")
        raise ValueError("GETGEMS_AUTH_TOKEN not set in .env")
    if not collection_address:
        logging.error("COLLECTION_ADDRESS not set in .env")
        raise ValueError("COLLECTION_ADDRESS not set in .env")

    # Log input parameters
    logging.info(f"GETGEMS_API_HOST: {api_host}")
    logging.info(f"COLLECTION_ADDRESS: {collection_address}")
    logging.info(f"Recipient Address: {address}")
    logging.info(f"Image IPFS: {image_ipfs}")
    logging.info(f"Metadata IPFS: {metadata_ipfs}")
    logging.info(f"Name: {name}")
    logging.info(f"Description: {description}")
    logging.info(f"Attributes: {attributes}")

    # Validate image_ipfs URL
    if not image_ipfs.startswith("https://"):
        logging.error(f"Invalid image_ipfs URL: {image_ipfs}")
        raise ValueError(f"Invalid image_ipfs URL: {image_ipfs}")
    try:
        response = requests.head(image_ipfs, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to access image URL {image_ipfs}: {str(e)}")
        raise

    # Validate metadata_ipfs URL
    if not metadata_ipfs.startswith("https://"):
        logging.error(f"Invalid metadata_ipfs URL: {metadata_ipfs}")
        raise ValueError(f"Invalid metadata_ipfs URL: {metadata_ipfs}")
    try:
        response = requests.get(metadata_ipfs, timeout=10)
        response.raise_for_status()
        metadata_json = response.json()
        logging.info(f"Metadata content: {metadata_json}")
        if not metadata_json.get("image"):
            logging.error("Metadata JSON missing 'image' field")
            raise ValueError("Metadata JSON missing 'image' field")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to access metadata URL {metadata_ipfs}: {str(e)}")
        raise

    # Form URL and headers for the request
    url = f"https://{api_host}/public-api/minting/{collection_address}"
    headers = {
        "accept": "application/json",
        "authorization": auth_token,
        "Content-Type": "application/json"
    }
    # Generate unique requestId
    request_id = str(int(time.time() * 1000))
    payload = {
        "requestId": request_id,
        "ownerAddress": address,
        "name": name,
        "description": description,
        "image": image_ipfs,
        "attributes": attributes
    }

    try:
        # Send POST request
        logging.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        logging.info(f"API response: {result}")

        # Handle 'in_queue' status
        if result.get("success") and result.get("response", {}).get("status") == "in_queue":
            logging.info("NFT in queue, checking status...")
            status_url = f"https://{api_host}/public-api/minting/{collection_address}/{request_id}"
            for _ in range(10):
                time.sleep(6)
                status_response = requests.get(status_url, headers=headers)
                status_response.raise_for_status()
                status_result = status_response.json()
                logging.info(f"Status: {status_result}")
                if status_result.get("success") and status_result.get("response", {}).get("status") == "ready":
                    logging.info(f"NFT successfully minted: {status_result}")
                    return {"success": True, "response": status_result.get("response", {})}
                return {"success": True, "response": result.get("response", {})}
        logging.info(f"Mint request successful: {result}")
        return {"success": True, "response": result.get("response", {})}
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error during minting: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Error during minting: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}