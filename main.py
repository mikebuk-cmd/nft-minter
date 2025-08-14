from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import tempfile
import time
from ai_image import generate_image
from ipfs_upload import upload_image_to_ipfs, upload_metadata_to_ipfs
from mint_nft import mint_nft
import logging
from dotenv import load_dotenv
import re

# Setup logging
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()

app = FastAPI()

# Serve static files from the 'static' directory
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Default TON recipient address
TON_RECIPIENT = os.getenv("TON_RECIPIENT", "0QCpruqZYuBMmCBrPTL2WOnQlMcJ5rQil4noKabCGRyzCtUD")

class GenerateImageRequest(BaseModel):
    prompt: str

class IpfsUploadRequest(BaseModel):
    filename: str
    prompt: str | None = None

class MintNFTRequest(BaseModel):
    address: str | None = None
    filename: str
    prompt: str | None = None

@app.post("/generate-image")
async def generate_image_endpoint(request: GenerateImageRequest):
    try:
        filename = generate_image(request.prompt)
        file_path = os.path.join(tempfile.gettempdir(), filename)
        if not os.path.exists(file_path):
            logging.error(f"Generated image not found: {file_path}")
            raise HTTPException(status_code=500, detail="Generated image not found")
        logging.info(f"Generated image: {filename}")
        return {"filename": filename, "message": "Image generated successfully"}
    except Exception as e:
        logging.error(f"Error generating image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image")
async def upload_image_endpoint(file: UploadFile = File(...)):
    try:
        # Validate file type
        if file.content_type not in ["image/png", "image/jpeg"]:
            logging.error(f"Invalid file type uploaded: {file.content_type}. Only PNG or JPEG allowed")
            raise HTTPException(status_code=400, detail="Only PNG or JPEG images are allowed")
        
        # Validate file size (max 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            logging.error("Uploaded image exceeds 5MB limit")
            raise HTTPException(status_code=400, detail="Image size must be less than 5MB")
        
        # Generate unique filename
        timestamp = int(time.time() * 1000)
        extension = "png" if file.content_type == "image/png" else "jpg"
        filename = f"uploaded_{timestamp}.{extension}"
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        logging.info(f"Image uploaded and saved as {file_path}")
        return {"filename": filename, "message": "Image uploaded successfully"}
    except Exception as e:
        logging.error(f"Error uploading image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-to-ipfs")
async def upload_to_ipfs_endpoint(request: IpfsUploadRequest):
    try:
        logging.info(f"Received IPFS upload request: filename={request.filename}, prompt={request.prompt}")
        if not request.filename:
            logging.error("Filename is empty or missing")
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Validate filename format
        if not re.match(r"^uploaded_\d+\.(png|jpg)$", request.filename):
            logging.error(f"Invalid filename format: {request.filename}")
            raise HTTPException(status_code=400, detail=f"Invalid filename format: {request.filename}. Expected 'uploaded_<timestamp>.png' or 'uploaded_<timestamp>.jpg'")
        
        file_path = os.path.join(tempfile.gettempdir(), request.filename)
        if not os.path.exists(file_path):
            logging.error(f"Image file not found: {file_path}")
            raise HTTPException(status_code=400, detail=f"Image file not found: {request.filename}")
        
        ipfs_image = upload_image_to_ipfs(file_path)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        description = f"Generated from: {request.prompt}" if request.prompt else "Uploaded image"
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", description, ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        return {"ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata, "filename": request.filename}
    except Exception as e:
        logging.error(f"Error uploading to IPFS: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"IPFS upload failed: {str(e)}")

@app.post("/mint-nft")
async def mint_nft_endpoint(request: MintNFTRequest):
    try:
        if request.address:
            if not re.match(r"^[0-9a-zA-Z_-]{48}$", request.address):
                logging.error("Invalid TON address format")
                raise HTTPException(status_code=400, detail="Invalid TON address format")
        else:
            request.address = TON_RECIPIENT
        
        file_path = os.path.join(tempfile.gettempdir(), request.filename)
        if not os.path.exists(file_path):
            logging.error(f"Image file not found for minting: {file_path}")
            raise HTTPException(status_code=400, detail="Image file not found")
        
        ipfs_image = upload_image_to_ipfs(file_path)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        description = f"Generated from: {request.prompt}" if request.prompt else "Uploaded image"
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", description, ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        result = mint_nft(request.address, ipfs_image, ipfs_metadata, name="Open Hack NFT", description=description)
        logging.info(f"Mint result: {result}")
        
        if result.get("success"):
            response = result.get("response", {})
            if response.get("status") == "ready":
                logging.info(f"NFT successfully minted to {request.address}")
                return {"message": f"NFT successfully minted to {request.address}", "url": response.get("url"), "ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata}
            else:
                logging.info(f"NFT queued for minting to {request.address}")
                return {"message": f"NFT queued for minting to {request.address}", "url": response.get("url"), "ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata}
        else:
            logging.error(f"Minting error: {result}")
            raise HTTPException(status_code=500, detail=f"Minting error: {result}")
    except Exception as e:
        logging.error(f"Error during minting: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image/{filename}")
async def get_image(filename: str):
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(file_path):
        logging.error(f"Image not found: {file_path}")
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")