"""
FastAPI Backend Application for AI/ML Hackathon Starter.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.llm import llm_client
from ai.prompts import DEFAULT_SYSTEM_PROMPT
from ml.model import train_baseline_model, save_model, load_model, DEFAULT_MODEL_PATH
from ml.prediction import make_prediction
from backend.core.config import ALLOWED_ORIGINS
from backend.core.database import init_db
import backend.models  # Ensures all ORM models are registered with Base.metadata
from backend.models.user import User
from backend.dependencies.auth import get_current_active_user, require_captain
import pandas as pd

load_dotenv()

app = FastAPI(
    title="Captain's Treasure Ledger API",
    description="Automated financial management system and treasury audit platform tailored to pirate economics.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    """Initialize database tables on application startup."""
    init_db()

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom OpenAPI configuration for Swagger Bearer Authentication
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT Bearer token obtained from POST /api/auth/login"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Register Core API Routers
from backend.routers import (
    ranks_router,
    crew_router,
    voyages_router,
    expenses_router,
    transactions_router,
    auth_router,
    users_router,
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ranks_router)
app.include_router(crew_router)
app.include_router(voyages_router)
app.include_router(expenses_router)
app.include_router(transactions_router)


# --- Request & Response Models ---

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    model_loaded: bool
    llm_provider: str


class AIGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or problem query for the AI")
    system_prompt: Optional[str] = Field(default=DEFAULT_SYSTEM_PROMPT, description="Optional system instructions")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1000, gt=0, le=4096)


class AIGenerateResponse(BaseModel):
    success: bool
    content: str
    provider: str
    model: str
    error: Optional[str] = None


class MLPredictRequest(BaseModel):
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ..., description="Feature dictionary or list of feature dictionaries"
    )


class MLPredictResponse(BaseModel):
    success: bool
    count: int
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None
    error: Optional[str] = None


class MLTrainRequest(BaseModel):
    records: List[Dict[str, Any]] = Field(..., description="List of row dictionaries for training")
    target_column: str = Field(..., description="Name of the target column to predict")
    task_type: Optional[str] = Field(default="classification", description="'classification' or 'regression'")
    n_estimators: Optional[int] = Field(default=100, gt=0, le=500)


class MLTrainResponse(BaseModel):
    success: bool
    metrics: Dict[str, Any]
    model_path: str
    error: Optional[str] = None


# --- API Routes ---

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify backend status, environment, and loaded assets."""
    is_model_loaded = os.path.exists(DEFAULT_MODEL_PATH)
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("ENVIRONMENT", "development"),
        model_loaded=is_model_loaded,
        llm_provider=llm_client.provider
    )


@app.post("/api/ai/generate", response_model=AIGenerateResponse)
def ai_generate(
    request: AIGenerateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate AI response using configured LLM provider or fallback mock."""
    try:
        res = llm_client.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1000
        )
        return AIGenerateResponse(**res)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}"
        )


@app.post("/api/ml/predict", response_model=MLPredictResponse)
def ml_predict(
    request: MLPredictRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Run model inference on input features."""
    res = make_prediction(request.data)
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error", "Prediction failed")
        )
    return MLPredictResponse(
        success=res["success"],
        count=res.get("count", 0),
        predictions=res.get("predictions", []),
        probabilities=res.get("probabilities"),
        error=res.get("error")
    )


@app.post("/api/ml/train", response_model=MLTrainResponse)
def ml_train(
    request: MLTrainRequest,
    captain_user: User = Depends(require_captain)
):
    """Train baseline ML pipeline on provided tabular dataset and save model."""
    try:
        df = pd.DataFrame(request.records)
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided dataset is empty"
            )

        pipeline, metrics = train_baseline_model(
            df=df,
            target_column=request.target_column,
            task_type=request.task_type or "classification",
            n_estimators=request.n_estimators or 100
        )

        saved_path = save_model(pipeline, DEFAULT_MODEL_PATH)

        return MLTrainResponse(
            success=True,
            metrics=metrics,
            model_path=saved_path,
            error=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
