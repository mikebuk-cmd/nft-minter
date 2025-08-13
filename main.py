from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import tempfile
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

class MintNFTRequest(BaseModel):
    address: str | None = None
    filename: str
    prompt: str | None = None  # Make prompt optional for uploaded images

@app.post("/generate-image")
async def generate_image_endpoint(request: GenerateImageRequest):
    try:
        filename = generate_image(request.prompt)
        file_path = os.path.join(tempfile.gettempdir(), filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Generated image not found")
        logging.info(f"Generated image: {filename}")
        return {"filename": filename, "message": "Image generated successfully"}
    except Exception as e:
        logging.exception("Error generating image")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image")
async def upload_image_endpoint(file: UploadFile = File(...)):
    try:
        # Validate file type
        if file.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(status_code=400, detail="Only PNG or JPEG images are allowed")
        
        # Validate file size (e.g., max 5MB)
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
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
        logging.exception("Error uploading image")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-to-ipfs")
async def upload_to_ipfs_endpoint(request: GenerateImageRequest | None = None):
    try:
        if request and request.prompt:
            filename = generate_image(request.prompt)
        else:
            raise HTTPException(status_code=400, detail="No prompt provided for generation and no uploaded image available")
        
        file_path = os.path.join(tempfile.gettempdir(), filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Image file not found")
        
        ipfs_image = upload_image_to_ipfs(file_path)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", f"Generated from: {request.prompt if request else 'Uploaded image'}", ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        return {"ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata, "filename": filename}
    except Exception as e:
        logging.exception("Error uploading to IPFS")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mint-nft")
async def mint_nft_endpoint(request: MintNFTRequest):
    try:
        if request.address:
            if not re.match(r"^[0-9a-zA-Z_-]{48}$", request.address):
                raise HTTPException(status_code=400, detail="Invalid TON address format")
        else:
            request.address = TON_RECIPIENT
        
        file_path = os.path.join(tempfile.gettempdir(), request.filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Image file not found")
        
        ipfs_image = upload_image_to_ipfs(file_path)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", f"Generated from: {request.prompt if request.prompt else 'Uploaded image'}", ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        result = mint_nft(request.address, ipfs_image, ipfs_metadata, name="Open Hack NFT", description=f"Generated from: {request.prompt if request.prompt else 'Uploaded image'}")
        logging.info(f"Mint result: {result}")
        
        if result.get("success"):
            response = result.get("response", {})
            if response.get("status") == "ready":
                return {"message": f"NFT successfully minted to {request.address}", "url": response.get("url"), "ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata}
            else:
                return {"message": f"NFT queued for minting to {request.address}", "url": response.get("url"), "ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata}
        else:
            raise HTTPException(status_code=500, detail=f"Minting error: {result}")
    except Exception as e:
        logging.exception("Error during minting")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image/{filename}")
async def get_image(filename: str):
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")