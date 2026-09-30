"""Plug-in point for the trained model (best of GRU-Autoencoder / Isolation Forest / One-Class SVM).

Until a model is deployed this returns None and the server relies on the ESP32 edge flag and the
continuous-flow rule. When your team has picked the winning model:

1. Train it in Jupyter, save it with joblib (scikit-learn) or model.save (Keras) into  ml_models/
2. Implement load + predict below, returning (is_anomaly: bool, score: float 0-1).
3. Mark the model as deployed via POST /api/ml/evaluations/ (is_deployed=true).
"""
from typing import Optional, Tuple


def predict_anomaly(reading) -> Optional[Tuple[bool, float]]:
    return None
