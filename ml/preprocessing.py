"""
Data preprocessing and feature engineering utilities.
"""

from typing import Tuple, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standard tabular dataframe cleanup:
    - Strips whitespace from string column names
    - Strips whitespace from string column values
    - Drops duplicated rows
    """
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()

    df = df.drop_duplicates()
    return df


def split_features_and_target(
    df: pd.DataFrame, target_column: str
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Split a DataFrame into feature matrix X and target vector y.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataframe columns: {list(df.columns)}")
    X = df.drop(columns=[target_column])
    y = df[target_column]
    return X, y


def split_train_test(
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[Any, Any, Any, Any]:
    """
    Split data into training and test partitions.
    """
    return train_test_split(X, y, test_size=test_size, random_state=random_state)


def build_tabular_preprocessor(
    numerical_cols: Optional[List[str]] = None,
    categorical_cols: Optional[List[str]] = None
) -> ColumnTransformer:
    """
    Build a standard Scikit-learn ColumnTransformer for tabular data.
    - Numericals: Median Imputation + Standard Scaling
    - Categoricals: Most-frequent Imputation + One-Hot Encoding (ignore unknown)
    """
    transformers = []

    if numerical_cols:
        num_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", num_pipeline, numerical_cols))

    if categorical_cols:
        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_pipeline, categorical_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop")
