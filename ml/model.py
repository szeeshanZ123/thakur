"""
Machine Learning model definitions, training routines, and persistence utilities.
"""

import os
import joblib
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from ml.preprocessing import build_tabular_preprocessor, split_features_and_target, split_train_test

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "baseline_model.joblib")


def train_baseline_model(
    df: pd.DataFrame,
    target_column: str,
    task_type: str = "classification",
    numerical_cols: Optional[list] = None,
    categorical_cols: Optional[list] = None,
    n_estimators: int = 100,
    random_state: int = 42
) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Train a complete baseline ML Pipeline (Preprocessor + Random Forest) on a DataFrame.
    Returns:
        (pipeline, metrics_dict)
    """
    X, y = split_features_and_target(df, target_column)

    # Auto-detect numerical and categorical columns if not explicitly provided
    if numerical_cols is None and categorical_cols is None:
        numerical_cols = list(X.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(X.select_dtypes(include=["object", "category", "string"]).columns)

    preprocessor = build_tabular_preprocessor(numerical_cols, categorical_cols)

    if task_type == "classification":
        estimator = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    else:
        estimator = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("estimator", estimator)
    ])

    X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.2, random_state=random_state)
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    metrics = {
        "task_type": task_type,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "numerical_features": numerical_cols,
        "categorical_features": categorical_cols,
    }

    if task_type == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        metrics["f1_weighted"] = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    else:
        metrics["mse"] = float(mean_squared_error(y_test, y_pred))
        metrics["r2"] = float(r2_score(y_test, y_pred))

    return pipeline, metrics


def save_model(model: Any, filepath: str = DEFAULT_MODEL_PATH) -> str:
    """
    Save trained model or pipeline to disk using joblib.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    joblib.dump(model, filepath)
    return filepath


def load_model(filepath: str = DEFAULT_MODEL_PATH) -> Optional[Any]:
    """
    Load a trained model or pipeline from disk using joblib.
    Returns None if file does not exist.
    """
    if not os.path.exists(filepath):
        return None
    return joblib.load(filepath)
