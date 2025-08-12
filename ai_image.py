import requests
import os
from dotenv import load_dotenv
import time
import logging

# Настройка логирования
logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Загружаем переменные из .env файла
load_dotenv()

def generate_image(prompt: str) -> str:
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        raise ValueError("❌ STABILITY_API_KEY не установлен в .env")

    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }
    files = {
        "prompt": (None, prompt),
        "model": (None, "stable-diffusion-xl-v1-0"),
        "output_format": (None, "png"),
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()

        # Генерируем уникальное имя файла с временной меткой
        timestamp = int(time.time() * 1000)
        filename = os.path.join(os.path.dirname(__file__), f"output_{timestamp}.png")
        with open(filename, "wb") as f:
            f.write(response.content)

        logging.info(f"Image generated and saved as {filename}")
        return filename
    except requests.exceptions.RequestException as e:
        logging.error(f"Error generating image: {str(e)}")
        raise