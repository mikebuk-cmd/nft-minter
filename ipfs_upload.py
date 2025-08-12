import requests
import os
from dotenv import load_dotenv
import json
import logging
import time

# Настройка логирования
logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Загружаем переменные из .env файла
load_dotenv()

def upload_image_to_ipfs(image_path: str) -> str:
    api_key = os.getenv("PINATA_API_KEY")
    secret_key = os.getenv("PINATA_SECRET_API_KEY")
    if not api_key or not secret_key:
        raise ValueError("❌ PINATA_API_KEY или PINATA_SECRET_API_KEY не установлены в .env")

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
                raise ValueError("❌ Не удалось получить IPFS hash для изображения")
            ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
            logging.info(f"Image uploaded to IPFS: {ipfs_url}")
            # Задержка для обеспечения доступности на IPFS
            time.sleep(5)
            # Проверяем доступность изображения
            response = requests.head(ipfs_url, timeout=10)
            if response.status_code != 200:
                raise ValueError(f"Image URL {ipfs_url} is not accessible: {response.status_code}")
            return ipfs_url
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading image to IPFS: {str(e)}")
            raise

def upload_metadata_to_ipfs(name: str, description: str, image_ipfs: str) -> str:
    api_key = os.getenv("PINATA_API_KEY")
    secret_key = os.getenv("PINATA_SECRET_API_KEY")
    if not api_key or not secret_key:
        raise ValueError("❌ PINATA_API_KEY или PINATA_SECRET_API_KEY не установлены в .env")

    # Формируем метаданные согласно спецификации GetGems
    metadata = {
        "name": name,
        "description": description,
        "image": image_ipfs,
        "attributes": [{"trait_type": "Background", "value": "Neon"}]
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False)
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
            raise ValueError("❌ Не удалось получить IPFS hash для метаданных")
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        logging.info(f"Metadata uploaded to IPFS: {ipfs_url}")
        # Задержка для обеспечения доступности на IPFS
        time.sleep(5)
        # Проверяем доступность метаданных
        response = requests.get(ipfs_url, timeout=10)
        if response.status_code != 200:
            raise ValueError(f"Metadata URL {ipfs_url} is not accessible: {response.status_code}")
        return ipfs_url
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading metadata to IPFS: {str(e)}")
        raise