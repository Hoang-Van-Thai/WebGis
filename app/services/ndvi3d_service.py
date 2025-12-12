# # app/services/ndvi3d_service.py
#
# import numpy as np
# import pickle
# from tensorflow.keras.models import load_model
# import os
#
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))
#
# MODEL_PATH = os.path.join(BASE_DIR, "models", "NDVI_3D_model.keras")
# SCALER_PATH = os.path.join(BASE_DIR, "models", "ndvi_scaler.pkl")
#
# # Load model + scaler khi import service
# model = load_model(MODEL_PATH)
#
# with open(SCALER_PATH, "rb") as f:
#     scaler = pickle.load(f)
#
# sequence_length = 10  # giống lúc train
#
#
# def predict_ndvi_3d(values):
#     """
#     values: list 10 số NDVI thực tế (REAL) — chưa scale
#     """
#
#     if len(values) != sequence_length:
#         return {"error": f"Cần đúng {sequence_length} giá trị NDVI đầu vào"}
#
#     # scale input
#     scaled = scaler.transform(np.array(values).reshape(-1, 1)).flatten()
#
#     X = np.array(scaled).reshape(1, sequence_length, 1)
#
#     pred_scaled = model.predict(X)[0][0]
#     pred_real = scaler.inverse_transform([[pred_scaled]])[0][0]
#
#     return {
#         "prediction_scaled": float(pred_scaled),
#         "prediction_real": float(pred_real)
#     }
import pandas as pd

def preprocess_ndvi(csv_path="ndvi_latest.csv"):
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])

    df_wide = df.pivot(index="date", columns="ten_xa", values="ndvi")
    df_wide = df_wide.interpolate(method="linear", limit_direction="both")

    df_long = df_wide.reset_index().melt(id_vars="date", var_name="ten_xa", value_name="ndvi")

    resampled = []
    for xa in df_long["ten_xa"].unique():
        sub = df_long[df_long["ten_xa"] == xa].copy()
        sub = sub.set_index("date")
        full_range = pd.date_range(sub.index.min(), sub.index.max(), freq="3D")
        sub = sub.reindex(full_range)
        sub["ten_xa"] = xa
        sub["ndvi"] = sub["ndvi"].interpolate(method="linear", limit_direction="both")
        sub = sub.reset_index().rename(columns={"index": "date"})
        resampled.append(sub)

    df_resampled = pd.concat(resampled)
    df_resampled = df_resampled.sort_values(["ten_xa", "date"])
    return df_resampled
