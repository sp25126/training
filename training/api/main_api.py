"""
FastAPI interface for the training project
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from main import UniversalQAGenerator

app = FastAPI(
    title="Training QA Generator API",
    description="QA generation with Llama integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global generator instance
generator = None

@app.on_event("startup")
async def startup_event():
    """Initialize the QA generator on startup"""
    global generator
    generator = UniversalQAGenerator()

# Request models
class TextResourceRequest(BaseModel):
    text: str
    dataset_name: Optional[str] = None

class WebResourceRequest(BaseModel):
    url: str
    dataset_name: Optional[str] = None

# API endpoints
@app.get("/")
async def root():
    return {
        "message": "Training QA Generator API",
        "version": "1.0.0",
        "features": ["text_processing", "web_scraping", "qa_generation", "dataset_building"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "generator_loaded": generator is not None
    }

@app.post("/process/text")
async def process_text_resource(request: TextResourceRequest):
    """Process text to generate QA dataset"""
    
    if not generator:
        raise HTTPException(status_code=503, detail="Generator not initialized")
    
    try:
        result = await generator.process_resource_to_dataset(
            resource=request.text,
            resource_type="text",
            dataset_name=request.dataset_name
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/web")
async def process_web_resource(request: WebResourceRequest):
    """Process web URL to generate QA dataset"""
    
    if not generator:
        raise HTTPException(status_code=503, detail="Generator not initialized")
    
    try:
        result = await generator.process_resource_to_dataset(
            resource=request.url,
            resource_type="web",
            dataset_name=request.dataset_name
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
