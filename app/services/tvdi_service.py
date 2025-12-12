# app/services/tvdi_service.py
import os
import numpy as np
import pickle
from tensorflow.keras.models import load_model

# Đường dẫn thư mục app/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(MODELS_DIR, "TVDI.keras")
SCALER_PATH = os.path.join(MODELS_DIR, "scalers.pkl")

# ====== LOAD MODEL VÀ SCALERS NGAY KHI IMPORT ======
model = load_model(MODEL_PATH)

with open(SCALER_PATH, "rb") as f:
    scalers = pickle.load(f)

WINDOW_SIZE = 18   # số timestep
N_FEATURES = 4     # mean_scaled, month_sin, month_cos, year_scaled
TARGET_SIZE = 3    # dự báo 3 bước


def predict_tvdi(xa_name: str, features_18x4):
    """
    xa_name: tên xã (string, ví dụ 'An Lạc')
    features_18x4: list hoặc mảng 18x4 (đã chuẩn hoá giống lúc train)
    """
    # Kiểm tra xã có trong scaler không
    if xa_name not in scalers:
        return {"error": f"Không tìm thấy scaler cho xã '{xa_name}' trong scalers.pkl"}

    # Chuyển input thành numpy
    arr = np.array(features_18x4, dtype="float32")

    # Kiểm tra kích thước
    if arr.shape != (WINDOW_SIZE, N_FEATURES):
        return {
            "error": f"Input phải có shape ({WINDOW_SIZE},{N_FEATURES}) "
                     f"nhưng nhận được {arr.shape}"
        }

    # Thêm batch dimension: (1, 18, 4)
    arr = np.expand_dims(arr, axis=0)

    # Dự đoán (ra giá trị đã scale)
    try:
        pred_scaled = model.predict(arr)[0]   # shape (3,)

        # Giải chuẩn hoá về TVDI thực
        scaler = scalers[xa_name]
        pred_real = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()

        return {
            "xa": xa_name,
            "prediction_scaled": pred_scaled.tolist(),
            "prediction_real": pred_real.tolist()
        }

    except Exception as e:
        return {"error": str(e)}
