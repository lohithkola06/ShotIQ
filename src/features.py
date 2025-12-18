import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


def build_feature_pipeline(df: pd.DataFrame):
    """
    Build a preprocessing pipeline for shot-make modeling.

    - numeric: passthrough
    - categorical: one-hot encode
    """
    numeric_features = ["LOC_X", "LOC_Y", "SHOT_DISTANCE", "YEAR"]
    categorical_features = ["SHOT_TYPE", "ACTION_TYPE"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

    return preprocessor, numeric_features + categorical_features

