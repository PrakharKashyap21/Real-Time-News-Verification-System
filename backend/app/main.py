from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
