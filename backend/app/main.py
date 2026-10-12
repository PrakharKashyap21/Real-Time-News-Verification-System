from contextlib import asynccontextmanager
import io
import os
import zipfile
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.app.schemas import PredictionRequest, PredictionResponse
from backend.app.predictor import get_predictor, NewsPredictor
from backend.app.v2.router import router as v2_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load models on application startup
    get_predictor()
    yield

app = FastAPI(
    title="TruthLens AI: Real-Time News & Claim Verification API",
    description="Agentic RAG and Large Language Model pipeline for real-time news verification and fact-checking",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for local React development and production simulation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register V2 verification endpoints
app.include_router(v2_router)
app.include_router(v2_router, prefix="/api")

@app.get("/", tags=["General"])
def read_root():
    return {
        "status": "ok",
        "service": "Fake News Detection API"
    }

@app.get("/health", tags=["General"])
def health_check():
    return {
        "status": "healthy"
    }

@app.get("/api/v2/extension/download", tags=["Extension"])
def download_extension_zip():
    """Package the Chrome Extension into an in-memory zip file for 1-click download."""
    extension_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "extension"))
    if not os.path.exists(extension_dir):
        raise HTTPException(status_code=404, detail="Extension directory not found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(extension_dir):
            for file in files:
                if file.startswith(".") or file.endswith(".tmp"):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extension_dir)
                zip_file.write(file_path, arcname=os.path.join("truthlens-extension", arcname))

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=truthlens-ai-chrome-extension.zip"}
    )

import logging

logger = logging.getLogger(__name__)

@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict_news(payload: PredictionRequest):
    try:
        predictor: NewsPredictor = get_predictor()
        result = predictor.predict(title=payload.title, text=payload.text)
        return PredictionResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error("Prediction service error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction service encountered an unexpected error. Please try again later."
        )
