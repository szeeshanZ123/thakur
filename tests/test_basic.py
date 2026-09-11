"""
Unit and integration tests for AI Hackathon Starter.
"""

import os
import sys
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

try:
    import pytest
    fixture = pytest.fixture
except ImportError:
    # Fallback dummy fixture decorator if pytest is not yet installed
    def fixture(fn):
        return fn


# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.models.user import User
from backend.dependencies.auth import get_current_active_user, require_captain
from ai.llm import LLMClient
from ai.prompts import format_hackathon_prompt, build_analysis_prompt
from ai.utils import extract_json_from_response, estimate_tokens, clean_text
from ml.preprocessing import clean_dataframe, split_features_and_target, build_tabular_preprocessor
from ml.model import train_baseline_model, save_model, load_model
from ml.prediction import make_prediction


@fixture
def client():
    mock_user = User(id=1, username="test_user", email="test@local", role="ADMIN", is_active=True)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[require_captain] = lambda: mock_user
    return TestClient(app)


def _make_sample_dataset():
    """Plain helper that builds the sample DataFrame (callable without pytest)."""
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "num_feature_1": np.random.randn(n),
        "num_feature_2": np.random.uniform(10, 50, n),
        "cat_feature": np.random.choice(["A", "B", "C"], n),
        "label": np.random.choice([0, 1], n)
    })
    return df


@fixture
def sample_dataset():
    return _make_sample_dataset()


# --- 1. AI Layer Tests ---

def test_prompt_formatting():
    prompt = format_hackathon_prompt(
        task_description="Classify Customer Sentiment",
        user_input="Great product!",
        output_format="json"
    )
    assert "Classify Customer Sentiment" in prompt
    assert "Great product!" in prompt
    assert "JSON object" in prompt


def test_ai_utils_json_extraction():
    raw_response = 'Here is the result: ```json\n{"status": "ok", "score": 95}\n``` Thanks!'
    parsed = extract_json_from_response(raw_response)
    assert parsed is not None
    assert parsed.get("status") == "ok"
    assert parsed.get("score") == 95


def test_ai_utils_token_and_text_clean():
    text = "  Hello world\r\nTest text  "
    cleaned = clean_text(text)
    assert cleaned == "Hello world\nTest text"
    tokens = estimate_tokens(cleaned)
    assert tokens > 0


def test_mock_llm_generation():
    client = LLMClient(provider="mock")
    res = client.generate(prompt="Analyze this hackathon problem.")
    assert res["success"] is True
    assert "AI Starter Mock Response" in res["content"]
    assert res["provider"] == "mock"


# --- 2. ML Layer Tests ---

def test_ml_preprocessing_and_training(sample_dataset, tmp_path):
    cleaned = clean_dataframe(sample_dataset)
    assert len(cleaned) == len(sample_dataset)

    pipeline, metrics = train_baseline_model(
        df=cleaned,
        target_column="label",
        task_type="classification",
        n_estimators=10
    )

    assert "accuracy" in metrics
    assert metrics["train_samples"] > 0

    # Test model saving & loading
    temp_model_path = str(tmp_path / "test_model.joblib")
    save_model(pipeline, temp_model_path)
    loaded_model = load_model(temp_model_path)
    assert loaded_model is not None

    # Test inference
    single_record = {"num_feature_1": 0.5, "num_feature_2": 25.0, "cat_feature": "A"}
    pred_res = make_prediction(single_record, model=loaded_model)
    assert pred_res["success"] is True
    assert len(pred_res["predictions"]) == 1


# --- 3. Backend API Route Tests ---

def test_backend_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_provider" in data


def test_backend_ai_generate_endpoint(client):
    payload = {"prompt": "What is the capital of France?"}
    response = client.post("/api/ai/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "content" in data


def test_backend_ml_train_and_predict_flow(client, sample_dataset):
    records = sample_dataset.to_dict(orient="records")
    train_payload = {
        "records": records,
        "target_column": "label",
        "task_type": "classification",
        "n_estimators": 10
    }

    train_resp = client.post("/api/ml/train", json=train_payload)
    assert train_resp.status_code == 200
    train_data = train_resp.json()
    assert train_data["success"] is True
    assert "accuracy" in train_data["metrics"]

    # Test predict endpoint with the newly trained model
    predict_payload = {
        "data": {
            "num_feature_1": 1.2,
            "num_feature_2": 30.5,
            "cat_feature": "B"
        }
    }
    pred_resp = client.post("/api/ml/predict", json=predict_payload)
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert pred_data["success"] is True
    assert len(pred_data["predictions"]) == 1


if __name__ == "__main__":
    print("=" * 60)
    print("Running AI Hackathon Starter Test Suite")
    print("=" * 60)

    # 1. AI tests
    print("[1/7] Testing prompt formatting...")
    test_prompt_formatting()
    print("  -> Passed")

    print("[2/7] Testing AI JSON extraction...")
    test_ai_utils_json_extraction()
    print("  -> Passed")

    print("[3/7] Testing AI token & text cleanup...")
    test_ai_utils_token_and_text_clean()
    print("  -> Passed")

    print("[4/7] Testing Mock LLM generation...")
    test_mock_llm_generation()
    print("  -> Passed")

    # 2. ML tests
    print("[5/7] Testing ML preprocessing, training & inference...")
    import tempfile
    import pathlib
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_p = pathlib.Path(temp_dir)
        df_sample = _make_sample_dataset()
        test_ml_preprocessing_and_training(df_sample, tmp_p)
    print("  -> Passed")

    # 3. Backend API tests
    print("[6/7] Testing FastAPI Health endpoint...")
    mock_user = User(id=1, username="test_user", email="test@local", role="ADMIN", is_active=True)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[require_captain] = lambda: mock_user
    c = TestClient(app)
    test_backend_health_endpoint(c)
    print("  -> Passed")

    print("[7/7] Testing Backend AI & ML endpoints...")
    test_backend_ai_generate_endpoint(c)
    test_backend_ml_train_and_predict_flow(c, _make_sample_dataset())
    print("  -> Passed")

    print("=" * 60)
    print("All 7 test suites passed successfully! [OK]")
    print("=" * 60)


