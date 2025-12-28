#!/usr/bin/env python3
"""
Script to retrain the NBA shot prediction model.
Run from project root: python scripts/retrain_model.py
"""
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, roc_auc_score

from src.data_loader import list_available_years, load_raw_shots, clean_shots, save_clean
from src.features import build_feature_pipeline

# XGBoost import with fallback
try:
    from xgboost import XGBClassifier
    xgb_available = True
except ImportError:
    xgb_available = False
    print("⚠️  XGBoost not available. Install with: pip install xgboost")
    print("   On macOS also run: brew install libomp")


def main():
    print("=" * 60)
    print("NBA Shot Prediction Model Retraining")
    print("=" * 60)
    
    # Step 1: Load and clean data
    available_years = list_available_years()
    print(f"\n📊 Available seasons: {available_years}")
    
    print("\n🔄 Loading raw shot data...")
    df_raw = load_raw_shots(years="all", n_rows=None)
    print(f"   Raw shape: {df_raw.shape}")
    
    print("\n🧹 Cleaning data...")
    df_clean = clean_shots(df_raw)
    print(f"   Cleaned shape: {df_clean.shape}")

    # Add player_name feature from canonical PLAYER_NAME column
    if "PLAYER_NAME" not in df_clean.columns:
        raise ValueError("PLAYER_NAME column missing after cleaning; cannot build player feature.")
    df_clean["player_name"] = df_clean["PLAYER_NAME"].astype(str).str.strip()
    
    # Save cleaned data
    save_clean(df_clean)
    print("   ✅ Saved clean data to data/nba_shots_clean.csv")
    
    # Step 2: Prepare features
    print("\n🔧 Preparing features...")
    # include player_name for player-specific probabilities
    X = df_clean[["LOC_X", "LOC_Y", "SHOT_DISTANCE", "YEAR", "SHOT_TYPE", "ACTION_TYPE", "player_name"]]
    y = df_clean["SHOT_MADE_FLAG"]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   Train size: {len(X_train)}, Test size: {len(X_test)}")
    
    # Step 3: Build preprocessor
    preprocessor, feature_list = build_feature_pipeline(df_clean)
    
    # Step 4: Train XGBoost model
    if not xgb_available:
        print("\n❌ Cannot train model without XGBoost. Exiting.")
        sys.exit(1)
    
    print("\n🚀 Training XGBoost model...")
    model_xgb = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "clf",
                XGBClassifier(
                    n_estimators=300,
                    learning_rate=0.05,
                    max_depth=6,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    eval_metric="logloss",
                    n_jobs=-1,
                ),
            ),
        ]
    )
    
    model_xgb.fit(X_train, y_train)
    
    # Step 5: Evaluate
    print("\n📈 Evaluating model...")
    y_pred = model_xgb.predict(X_test)
    y_prob = model_xgb.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    
    print(f"   Accuracy: {acc:.3f}")
    print(f"   ROC-AUC:  {auc:.3f}")
    
    # Step 6: Save model
    model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "shot_model_xgb.pkl")
    joblib.dump(model_xgb, model_path)
    print(f"\n💾 Saved model to {model_path}")
    
    # Also save to notebooks/models for notebook compatibility
    notebooks_model_dir = os.path.join(os.path.dirname(__file__), "..", "notebooks", "models")
    os.makedirs(notebooks_model_dir, exist_ok=True)
    notebooks_model_path = os.path.join(notebooks_model_dir, "shot_model_xgb.pkl")
    joblib.dump(model_xgb, notebooks_model_path)
    print(f"   Also saved to {notebooks_model_path}")
    
    print("\n" + "=" * 60)
    print("✅ Model retraining complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
