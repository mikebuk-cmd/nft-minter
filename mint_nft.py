import requests
import os
from dotenv import load_dotenv
import time
import logging

# Настройка логирования
logging.basicConfig(filename="getgems_mint.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Загружаем переменные из .env файла
load_dotenv()

def mint_nft(recipient_address: str, image_ipfs: str, metadata_ipfs: str, name: str, description: str):
    # Получаем переменные окружения
    api_host = os.getenv("GETGEMS_API_HOST", "api.testnet.getgems.io")
    auth_token = os.getenv("GETGEMS_AUTH_TOKEN")
    collection_address = os.getenv("COLLECTION_ADDRESS")

    # Проверяем наличие необходимых переменных
    if not auth_token:
        raise ValueError("❌ GETGEMS_AUTH_TOKEN не установлен в .env")
    if not collection_address:
        raise ValueError("❌ COLLECTION_ADDRESS не установлен в .env")

    # Логируем входные параметры
    logging.info(f"GETGEMS_API_HOST: {api_host}")
    logging.info(f"COLLECTION_ADDRESS: {collection_address}")
    logging.info(f"Recipient Address: {recipient_address}")
    logging.info(f"Image IPFS: {image_ipfs}")
    logging.info(f"Metadata IPFS: {metadata_ipfs}")
    logging.info(f"Name: {name}")
    logging.info(f"Description: {description}")

    # Проверяем доступность изображения
    if not image_ipfs.startswith("https://"):
        raise ValueError(f"❌ Invalid image_ipfs URL: {image_ipfs}")
    try:
        response = requests.head(image_ipfs, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to access image URL {image_ipfs}: {str(e)}")
        raise

    # Проверяем доступность метаданных
    if not metadata_ipfs.startswith("https://"):
        raise ValueError(f"❌ Invalid metadata_ipfs URL: {metadata_ipfs}")
    try:
        response = requests.get(metadata_ipfs, timeout=10)
        response.raise_for_status()
        metadata_json = response.json()
        logging.info(f"Metadata content: {metadata_json}")
        if not metadata_json.get("image"):
            raise ValueError("❌ Metadata JSON missing 'image' field")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to access metadata URL {metadata_ipfs}: {str(e)}")
        raise

    # Формируем URL и заголовки для запроса
    url = f"https://{api_host}/public-api/minting/{collection_address}"
    headers = {
        "accept": "application/json",
        "authorization": auth_token,
        "Content-Type": "application/json"
    }
    # Генерируем уникальный requestId
    request_id = str(int(time.time() * 1000))
    payload = {
        "requestId": request_id,
        "ownerAddress": recipient_address,
        "name": name,
        "description": description,
        "image": image_ipfs,  # Use image_ipfs, not metadata_ipfs
        "attributes": [{"trait_type": "Background", "value": "Neon"}]
    }

    try:
        # Отправляем POST-запрос
        logging.info(f"Sending POST request to {url}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        logging.info(f"API response: {result}")

        # Если статус "in_queue", проверяем статус
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
                    return status_result
            logging.warning("NFT still in queue after 10 attempts")
            return result
        return result
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Error: {str(e)}")
        raise