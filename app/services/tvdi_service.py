# app/services/tvdi_service.py
import os
import numpy as np
import pickle
from tensorflow.keras.models import load_model
import pandas as pd
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

def _parse_month_start(last_date) -> pd.Timestamp:
    """
    last_date có thể là datetime / Timestamp / string.
    Trả về Timestamp đầu tháng.
    """
    t = pd.to_datetime(last_date, errors="coerce")
    if pd.isna(t):
        raise ValueError(f"last_date không hợp lệ: {last_date}")
    return t.to_period("M").to_timestamp(how="start")

def _month_features(dt: pd.Timestamp, year_min: int, year_max: int):
    m = int(dt.month)
    month_sin = np.sin(2 * np.pi * m / 12.0)
    month_cos = np.cos(2 * np.pi * m / 12.0)
    if year_max == year_min:
        year_scaled = 0.0
    else:
        year_scaled = (dt.year - year_min) / (year_max - year_min)
    return float(month_sin), float(month_cos), float(year_scaled)

def predict_tvdi_next_7_from_seq(
    xa_name: str,
    seq_18x4,
    last_date,
    year_min: int,
    year_max: int
):
    """
    seq_18x4: numpy array shape (18,4) theo format:
      [mean_scaled, month_sin, month_cos, year_scaled]
    last_date: ngày cuối cùng của history (datetime/Timestamp/string)
    year_min/year_max: dùng để tính year_scaled cho tương lai (nên lấy theo df đang dùng)
    """
    if xa_name not in scalers:
        return {"error": f"Không tìm thấy scaler cho xã '{xa_name}' trong scalers.pkl"}

    seq = np.array(seq_18x4, dtype="float32")
    if seq.shape != (WINDOW_SIZE, N_FEATURES):
        return {"error": f"seq phải có shape ({WINDOW_SIZE},{N_FEATURES}) nhưng nhận {seq.shape}"}

    scaler = scalers[xa_name]
    base_month = _parse_month_start(last_date)

    preds_scaled = []
    preds_real = []

    while len(preds_real) < 7:
        X = np.expand_dims(seq, axis=0)        # (1,18,4)
        pred_scaled_3 = model.predict(X)[0]    # (3,)

        pred_real_3 = scaler.inverse_transform(pred_scaled_3.reshape(-1, 1)).flatten()

        # append đủ 7
        for i in range(3):
            if len(preds_real) >= 7:
                break
            preds_scaled.append(float(pred_scaled_3[i]))
            preds_real.append(float(pred_real_3[i]))

        # update seq theo từng bước (quan trọng: update month_sin/cos theo tháng tương lai)
        for i in range(3):
            # bước tương lai thứ k (k bắt đầu từ 1)
            k = len(preds_scaled) - (3 - i)  # k = 1..n
            future_month = base_month + pd.DateOffset(months=k)

            m_sin, m_cos, y_scaled = _month_features(future_month, year_min, year_max)

            new_vec = seq[-1].copy()
            new_vec[0] = float(pred_scaled_3[i])
            new_vec[1] = m_sin
            new_vec[2] = m_cos
            new_vec[3] = y_scaled

            seq = np.vstack([seq[1:], new_vec])

            if len(preds_real) >= 7:
                break

    return {
        "xa": xa_name,
        "prediction_scaled_7": preds_scaled[:7],
        "prediction_real_7": preds_real[:7],
        "last_month": base_month.strftime("%Y-%m"),
    }


# app/services/tvdi_service.py
# import os
# import numpy as np
# import pickle
# import pandas as pd
# from tensorflow.keras.models import load_model
#
# # Đường dẫn thư mục app/
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# MODELS_DIR = os.path.join(BASE_DIR, "models")
#
# MODEL_PATH = os.path.join(MODELS_DIR, "TVDI.keras")
# SCALER_PATH = os.path.join(MODELS_DIR, "scalers.pkl")
#
# # ====== LOAD MODEL VÀ SCALERS NGAY KHI IMPORT ======
# model = load_model(MODEL_PATH)
#
# with open(SCALER_PATH, "rb") as f:
#     scalers = pickle.load(f)
#
# WINDOW_SIZE = 18   # số timestep
# N_FEATURES = 4     # mean_scaled, month_sin, month_cos, year_scaled
# TARGET_SIZE = 3    # model dự báo 3 bước / 1 lần predict
#
#
# def predict_tvdi(xa_name: str, features_18x4):
#     """
#     Dự báo 3 bước (GIỮ NGUYÊN LOGIC CŨ).
#     xa_name: tên xã (string, ví dụ 'An Lạc')
#     features_18x4: list hoặc mảng 18x4 (đã chuẩn hoá giống lúc train)
#     """
#     if xa_name not in scalers:
#         return {"error": f"Không tìm thấy scaler cho xã '{xa_name}' trong scalers.pkl"}
#
#     arr = np.array(features_18x4, dtype="float32")
#
#     if arr.shape != (WINDOW_SIZE, N_FEATURES):
#         return {
#             "error": f"Input phải có shape ({WINDOW_SIZE},{N_FEATURES}) nhưng nhận được {arr.shape}"
#         }
#
#     arr = np.expand_dims(arr, axis=0)  # (1,18,4)
#
#     try:
#         pred_scaled = model.predict(arr)[0]  # (3,)
#
#         scaler = scalers[xa_name]
#         pred_real = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
#
#         return {
#             "xa": xa_name,
#             "prediction_scaled": pred_scaled.tolist(),
#             "prediction_real": pred_real.tolist(),
#         }
#     except Exception as e:
#         return {"error": str(e)}
#
#
# # =========================
# # NEW: Dự báo 7 bước
# # =========================
#
# def _parse_month_start(last_month: str) -> pd.Timestamp:
#     """
#     Nhận 'YYYY-MM' hoặc 'YYYY-MM-DD' -> trả Timestamp đầu tháng 'YYYY-MM-01'
#     """
#     s = str(last_month).strip()
#     s = s[:7]  # YYYY-MM
#     t = pd.to_datetime(s + "-01", errors="coerce")
#     if pd.isna(t):
#         raise ValueError(f"last_month không hợp lệ: {last_month}")
#     return t
#
#
# def _month_features(dt: pd.Timestamp, year_min: int, year_max: int):
#     """
#     Tạo month_sin, month_cos, year_scaled cho tháng dt.
#     """
#     m = int(dt.month)
#     month_sin = np.sin(2 * np.pi * m / 12.0)
#     month_cos = np.cos(2 * np.pi * m / 12.0)
#
#     if year_max == year_min:
#         year_scaled = 0.0
#     else:
#         year_scaled = (dt.year - year_min) / (year_max - year_min)
#
#     return float(month_sin), float(month_cos), float(year_scaled)
#
#
# def predict_tvdi_next_7(xa_name: str, features_18x4, last_month: str, year_min: int = 2000, year_max: int = 2035):
#     """
#     Dự báo 7 bước TVDI tiếp theo (KHÔNG đổi model, model vẫn output 3).
#
#     Cách làm:
#     - Gọi model predict ra 3 bước
#     - Append kết quả cho đủ 7
#     - Roll cửa sổ (shift) và thêm từng bước mới vào chuỗi (autoreg)
#     - Mỗi bước mới cập nhật month_sin/month_cos/year_scaled theo tháng tương lai
#
#     Inputs:
#       - xa_name: tên xã
#       - features_18x4: shape (18,4) đúng format [mean_scaled, month_sin, month_cos, year_scaled]
#       - last_month: tháng cuối của history (vd '2025-11' hoặc '2025-11-15')
#       - year_min/year_max: để scale year ổn định cho tương lai
#
#     Output:
#       {
#         "xa": ...,
#         "last_month": "YYYY-MM",
#         "prediction_real_7": [7 giá trị thực],
#         "prediction_scaled_7": [7 giá trị scale]
#       }
#     """
#     if xa_name not in scalers:
#         return {"error": f"Không tìm thấy scaler cho xã '{xa_name}' trong scalers.pkl"}
#
#     seq = np.array(features_18x4, dtype="float32")
#     if seq.shape != (WINDOW_SIZE, N_FEATURES):
#         return {"error": f"Input phải có shape ({WINDOW_SIZE},{N_FEATURES}) nhưng nhận được {seq.shape}"}
#
#     scaler = scalers[xa_name]
#     base_month = _parse_month_start(last_month)
#
#     preds_scaled_7 = []
#     preds_real_7 = []
#
#     # model trả 3 bước mỗi lần -> gọi lặp tới khi đủ 7
#     while len(preds_real_7) < 7:
#         X = np.expand_dims(seq, axis=0)      # (1,18,4)
#         pred_scaled_3 = model.predict(X)[0]  # (3,)
#
#         # inverse -> real
#         pred_real_3 = scaler.inverse_transform(pred_scaled_3.reshape(-1, 1)).flatten()
#
#         # add vào list (cắt đủ 7)
#         for i in range(len(pred_scaled_3)):
#             if len(preds_real_7) >= 7:
#                 break
#
#             preds_scaled_7.append(float(pred_scaled_3[i]))
#             preds_real_7.append(float(pred_real_3[i]))
#
#         # roll seq theo từng bước 1 để update feature thời gian chuẩn
#         # (không thêm 3 cục một lần kiểu copy feature cũ)
#         for i in range(len(pred_scaled_3)):
#             # tháng tương lai tương ứng bước (len đã có trước khi push step này)
#             # vì mỗi step là +1 month
#             step_index = len(preds_scaled_7) - (len(pred_scaled_3) - i)  # 1-based-ish
#             future_month = base_month + pd.DateOffset(months=step_index)
#
#             m_sin, m_cos, y_scaled = _month_features(future_month, year_min, year_max)
#
#             new_vec = seq[-1].copy()
#             new_vec[0] = float(pred_scaled_3[i])  # mean_scaled
#             new_vec[1] = m_sin
#             new_vec[2] = m_cos
#             new_vec[3] = y_scaled
#
#             seq = np.vstack([seq[1:], new_vec])
#
#             # nếu đã đủ 7 thì có thể dừng update sớm
#             if len(preds_real_7) >= 7:
#                 break
#
#     return {
#         "xa": xa_name,
#         "last_month": base_month.strftime("%Y-%m"),
#         "prediction_scaled_7": preds_scaled_7[:7],
#         "prediction_real_7": preds_real_7[:7],
#     }
