import os
import logging
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "lgbm_model.pkl")


class AIModel:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.last_train_time = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    data = pickle.load(f)
                self.model = data["model"]
                self.is_trained = True
                self.last_train_time = data.get("trained_at")
                logger.info("Model loaded from disk")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

    def _save_model(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({
                "model": self.model,
                "trained_at": datetime.utcnow().isoformat(),
            }, f)

    def train(self, features_df: pd.DataFrame, feature_columns: list[str]):
        try:
            import lightgbm as lgb
            from sklearn.model_selection import TimeSeriesSplit

            df = features_df.copy()
            df["target"] = 0
            future_return = df["close"].shift(-5) / df["close"] - 1
            df.loc[future_return > 0.002, "target"] = 1
            df.loc[future_return < -0.002, "target"] = 2

            df = df.dropna(subset=feature_columns + ["target"])
            if len(df) < 100:
                logger.warning("Not enough data for training")
                return False

            X = df[feature_columns].values
            y = df["target"].values.astype(int)

            split_idx = int(len(X) * 0.8)
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]

            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            params = {
                "objective": "multiclass",
                "num_class": 3,
                "metric": "multi_logloss",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "min_child_samples": 20,
                "reg_alpha": 0.1,
                "reg_lambda": 0.1,
                "verbose": -1,
                "n_jobs": -1,
            }

            callbacks = [lgb.early_stopping(50), lgb.log_evaluation(0)]
            self.model = lgb.train(
                params, train_data,
                num_boost_round=500,
                valid_sets=[val_data],
                callbacks=callbacks,
            )
            self.is_trained = True
            self.last_train_time = datetime.utcnow().isoformat()
            self._save_model()
            logger.info(f"Model trained on {len(X_train)} samples, val size {len(X_val)}")
            return True
        except Exception as e:
            logger.error(f"Training error: {e}")
            return False

    def predict(self, features: np.ndarray) -> dict:
        if not self.is_trained or self.model is None:
            return {"signal": "HOLD", "confidence": 0.0, "probabilities": {}}

        try:
            if features.ndim == 1:
                features = features.reshape(1, -1)
            proba = self.model.predict(features)[0]
            hold_prob = proba[0]
            buy_prob = proba[1]
            sell_prob = proba[2]

            max_idx = np.argmax(proba)
            signals = {0: "HOLD", 1: "BUY", 2: "SELL"}
            signal = signals[max_idx]
            confidence = float(proba[max_idx]) * 100

            return {
                "signal": signal,
                "confidence": confidence,
                "probabilities": {
                    "HOLD": round(hold_prob * 100, 2),
                    "BUY": round(buy_prob * 100, 2),
                    "SELL": round(sell_prob * 100, 2),
                },
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "probabilities": {}}

    def get_status(self) -> dict:
        return {
            "is_trained": self.is_trained,
            "last_train_time": self.last_train_time,
            "model_type": "LightGBM" if self.is_trained else "Not trained",
        }
