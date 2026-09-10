"""
Model inference and prediction routines.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from ml.model import load_model, DEFAULT_MODEL_PATH


def make_prediction(
    input_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    model: Optional[Any] = None,
    model_path: str = DEFAULT_MODEL_PATH
) -> Dict[str, Any]:
    """
    Run prediction inference on single record (dict), list of records, or DataFrame.
    """
    # Load model if not provided
    if model is None:
        model = load_model(model_path)
        if model is None:
            return {
                "success": False,
                "error": f"No trained model found at '{model_path}'. Please train a model first.",
                "predictions": []
            }

    # Convert input to DataFrame
    if isinstance(input_data, dict):
        df = pd.DataFrame([input_data])
    elif isinstance(input_data, list):
        df = pd.DataFrame(input_data)
    elif isinstance(input_data, pd.DataFrame):
        df = input_data.copy()
    else:
        return {
            "success": False,
            "error": f"Unsupported input_data type: {type(input_data)}",
            "predictions": []
        }

    try:
        raw_preds = model.predict(df)
        preds = [int(p) if isinstance(p, (np.integer, bool)) else (float(p) if isinstance(p, (np.floating, float)) else str(p)) for p in raw_preds]

        result = {
            "success": True,
            "count": len(preds),
            "predictions": preds,
            "error": None
        }

        # Check if predict_proba is available (classification)
        if hasattr(model, "predict_proba"):
            try:
                probs = model.predict_proba(df)
                result["probabilities"] = probs.tolist()
            except Exception:
                pass

        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Inference error: {str(e)}",
            "predictions": []
        }
