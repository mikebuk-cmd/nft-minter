from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
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

# Default TON recipient address
TON_RECIPIENT = os.getenv("TON_RECIPIENT", "0QCpruqZYuBMmCBrPTL2WOnQlMcJ5rQil4noKabCGRyzCtUD")

class GenerateImageRequest(BaseModel):
    prompt: str

class MintNFTRequest(BaseModel):
    address: str
    filename: str
    prompt: str

@app.post("/generate-image")
async def generate_image_endpoint(request: GenerateImageRequest):
    try:
        filename = generate_image(request.prompt)
        if not os.path.exists(filename):
            raise HTTPException(status_code=500, detail="Generated image not found")
        logging.info(f"Generated image: {filename}")
        return {"filename": filename, "message": "Image generated successfully"}
    except Exception as e:
        logging.exception("Error generating image")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-to-ipfs")
async def upload_to_ipfs_endpoint(request: GenerateImageRequest):
    try:
        filename = generate_image(request.prompt)
        if not os.path.exists(filename):
            raise HTTPException(status_code=500, detail="Image file not found")
        
        ipfs_image = upload_image_to_ipfs(filename)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", f"Generated from: {request.prompt}", ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        return {"ipfs_image": ipfs_image, "ipfs_metadata": ipfs_metadata, "filename": filename}
    except Exception as e:
        logging.exception("Error uploading to IPFS")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mint-nft")
async def mint_nft_endpoint(request: MintNFTRequest):
    try:
        # Validate TON address
        if not re.match(r"^[0-9a-zA-Z_-]{48}$", request.address):
            raise HTTPException(status_code=400, detail="Invalid TON address format")
        
        if not os.path.exists(request.filename):
            raise HTTPException(status_code=400, detail="Image file not found")
        
        ipfs_image = upload_image_to_ipfs(request.filename)
        logging.info(f"Image uploaded to IPFS: {ipfs_image}")
        
        ipfs_metadata = upload_metadata_to_ipfs("Open Hack NFT", f"Generated from: {request.prompt}", ipfs_image)
        logging.info(f"Metadata uploaded to IPFS: {ipfs_metadata}")
        
        result = mint_nft(request.address, ipfs_image, ipfs_metadata, name="Open Hack NFT", description=f"Generated from: {request.prompt}")
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
    file_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)