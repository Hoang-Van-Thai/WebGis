#
# import pandas as pd
# import numpy as np
# import pickle
# from tensorflow.keras.models import load_model
# from app.services.ndvi3d_service import preprocess_ndvi
#
# SEQUENCE = 10          # số bước đầu vào, giống lúc train
# N_STEPS = 7            # số bước muốn dự đoán tiếp theo
# MODEL = "app/models/NDVI_3D_model.keras"
# SCALER = "app/models/ndvi_scaler.pkl"
#
#
# def predict_next_n_steps(model, scaler, last_seq_scaled, n_steps=N_STEPS):
#     """
#     Dùng mô hình 1-step để dự đoán nhiều bước:
#     - last_seq_scaled: mảng NDVI đã scale, độ dài = SEQUENCE
#     - trả về: list NDVI thật (đã inverse_scale), độ dài = n_steps
#     """
#     seq = np.array(last_seq_scaled, dtype=float).copy()
#     preds_real = []
#
#     for _ in range(n_steps):
#         X = seq.reshape(1, SEQUENCE, 1)
#         pred_scaled = model.predict(X, verbose=0)[0, 0]
#
#         pred_real = scaler.inverse_transform([[pred_scaled]])[0, 0]
#         preds_real.append(float(pred_real))
#
#         seq = np.append(seq[1:], pred_scaled)
#
#     return preds_real
#
#
# def run_ndvi_prediction(n_steps=N_STEPS):
#     df = preprocess_ndvi()
#
#     scaler = pickle.load(open(SCALER, "rb"))
#     model = load_model(MODEL)
#
#     results = []
#
#     for xa in df["ten_xa"].unique():
#         sub = df[df["ten_xa"] == xa].sort_values("date")
#         ndvi_vals = sub["ndvi"].values.reshape(-1, 1)
#
#         if len(ndvi_vals) < SEQUENCE:
#             continue
#
#         scaled = scaler.transform(ndvi_vals).flatten()
#         last_seq = scaled[-SEQUENCE:]
#
#         preds_real = predict_next_n_steps(model, scaler, last_seq, n_steps)
#
#         last_date = sub["date"].max()
#         future_dates = [
#             last_date + pd.Timedelta(days=3 * i)
#             for i in range(1, n_steps + 1)
#         ]
#
#         for step, (d, v) in enumerate(zip(future_dates, preds_real), start=1):
#             results.append({
#                 "ten_xa": xa,
#                 "step": step,
#                 "date": d,
#                 "predicted_ndvi": v
#             })
#
#     pd.DataFrame(results).to_csv("ndvi_prediction.csv", index=False, encoding="utf-8-sig")
#     return results
# def predict_ndvi_by_xa(xa_name, n_steps=N_STEPS):
#     df = preprocess_ndvi()
#
#     scaler = pickle.load(open(SCALER, "rb"))
#     model = load_model(MODEL)
#
#     # Lọc dữ liệu theo xã
#     sub = df[df["ten_xa"] == xa_name].sort_values("date")
#     if sub.empty:
#         return {"error": f"Không có dữ liệu NDVI cho xã {xa_name}"}
#
#     ndvi_vals = sub["ndvi"].values.reshape(-1, 1)
#
#     if len(ndvi_vals) < SEQUENCE:
#         return {"error": f"Không đủ dữ liệu NDVI để dự báo cho xã {xa_name}"}
#
#     # Lấy 10 bước cuối
#     scaled = scaler.transform(ndvi_vals).flatten()
#     last_seq = scaled[-SEQUENCE:]
#
#     # Dự báo nhiều bước
#     preds_real = predict_next_n_steps(model, scaler, last_seq, n_steps)
#
#     last_date = sub["date"].max()
#     future_dates = [
#         last_date + pd.Timedelta(days=3 * i)
#         for i in range(1, n_steps + 1)
#     ]
#
#     results = []
#     for step, (d, v) in enumerate(zip(future_dates, preds_real), start=1):
#         results.append({
#             "ten_xa": xa_name,
#             "step": step,
#             "date": d,
#             "predicted_ndvi": v
#         })
#
#     return results
# def ndvi_get_history(xa, n=50):
#     df = preprocess_ndvi()
#     df = df[df["ten_xa"] == xa].sort_values("date")
#
#     if df.empty:
#         return []
#
#     return [
#         {"date": str(row.date.date()), "value": float(row.ndvi)}
#         for _, row in df.tail(n).iterrows()
#     ]
# def ndvi_history_with_forecast(xa, n_steps=7):
#     history = ndvi_get_history(xa)
#     forecast_raw = predict_ndvi_by_xa(xa, n_steps)
#
#     if isinstance(forecast_raw, dict) and "error" in forecast_raw:
#         return forecast_raw
#
#     forecast = [
#         {"date": str(item["date"].date()), "value": float(item["predicted_ndvi"])}
#         for item in forecast_raw
#     ]
#
#     return {
#         "xa": xa,
#         "history": history,
#         "forecast": forecast
#     }
# app/services/ndvi_auto_predict.py

import pandas as pd
import numpy as np
import pickle
from tensorflow.keras.models import load_model

from app.db.mongo import ndvi_col   # DÙNG MONGO, KHÔNG DÙNG CSV NỮA

SEQUENCE = 10          # số bước đầu vào, giống lúc train
N_STEPS = 7            # số bước muốn dự đoán tiếp theo
MODEL = "app/models/NDVI_3D_model.keras"
SCALER = "app/models/ndvi_scaler.pkl"


# ==============================
# 1. PREPROCESS NDVI TỪ MONGODB
# ==============================

def preprocess_ndvi():
    """
    Đọc toàn bộ NDVI từ Mongo (ndvi_history),
    nội suy theo thời gian,
    resample mỗi 3 ngày,
    trả về df có cột: ten_xa, date, ndvi
    """
    docs = list(ndvi_col.find().sort("date", 1))

    if not docs:
        return pd.DataFrame(columns=["ten_xa", "date", "ndvi"])

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])

    # Chỉ giữ các cột cần thiết
    df = df[["ten_xa", "date", "ndvi"]]

    # Pivot sang wide để nội suy theo thời gian
    df_wide = df.pivot(index="date", columns="ten_xa", values="ndvi")
    df_wide = df_wide.interpolate(method="linear", limit_direction="both")

    # Quay về dạng long
    df_long = (
        df_wide
        .reset_index()
        .melt(id_vars="date", var_name="ten_xa", value_name="ndvi")
    )

    # Resample mỗi 3 ngày cho từng xã
    resampled = []
    for xa in df_long["ten_xa"].unique():
        sub = df_long[df_long["ten_xa"] == xa].copy()
        sub = sub.set_index("date").sort_index()

        full_range = pd.date_range(sub.index.min(), sub.index.max(), freq="3D")
        sub = sub.reindex(full_range)
        sub["ten_xa"] = xa
        sub["ndvi"] = sub["ndvi"].interpolate(method="linear", limit_direction="both")

        sub = sub.reset_index().rename(columns={"index": "date"})
        resampled.append(sub)

    df_resampled = pd.concat(resampled)
    df_resampled = df_resampled.sort_values(["ten_xa", "date"])

    return df_resampled


# ====================
# 2. HÀM DỰ BÁO NDVI
# ====================

def predict_next_n_steps(model, scaler, last_seq_scaled, n_steps=N_STEPS):
    """
    Dùng mô hình 1-step để dự đoán nhiều bước:
    - last_seq_scaled: mảng NDVI đã scale, độ dài = SEQUENCE
    - trả về: list NDVI thật (đã inverse_scale), độ dài = n_steps
    """
    seq = np.array(last_seq_scaled, dtype=float).copy()
    preds_real = []

    for _ in range(n_steps):
        X = seq.reshape(1, SEQUENCE, 1)
        pred_scaled = model.predict(X, verbose=0)[0, 0]

        pred_real = scaler.inverse_transform([[pred_scaled]])[0, 0]
        preds_real.append(float(pred_real))

        # dịch sang trái và thêm giá trị dự báo mới
        seq = np.append(seq[1:], pred_scaled)

    return preds_real


def run_ndvi_prediction(n_steps=N_STEPS):
    df = preprocess_ndvi()  # GIỜ LẤY TỪ MONGO

    scaler = pickle.load(open(SCALER, "rb"))
    model = load_model(MODEL)

    results = []

    for xa in df["ten_xa"].unique():
        sub = df[df["ten_xa"] == xa].sort_values("date")
        ndvi_vals = sub["ndvi"].values.reshape(-1, 1)

        if len(ndvi_vals) < SEQUENCE:
            continue

        scaled = scaler.transform(ndvi_vals).flatten()
        last_seq = scaled[-SEQUENCE:]

        preds_real = predict_next_n_steps(model, scaler, last_seq, n_steps)

        last_date = sub["date"].max()
        future_dates = [
            last_date + pd.Timedelta(days=3 * i)
            for i in range(1, n_steps + 1)
        ]

        for step, (d, v) in enumerate(zip(future_dates, preds_real), start=1):
            results.append({
                "ten_xa": xa,
                "step": step,
                "date": d,
                "predicted_ndvi": v
            })

    # vẫn có thể dump ra CSV nếu bạn muốn debug, hoặc bỏ dòng dưới
    pd.DataFrame(results).to_csv("ndvi_prediction.csv", index=False, encoding="utf-8-sig")
    return results


def predict_ndvi_by_xa(xa_name, n_steps=N_STEPS):
    df = preprocess_ndvi()  # GIỜ LẤY TỪ MONGO

    scaler = pickle.load(open(SCALER, "rb"))
    model = load_model(MODEL)

    # Lọc dữ liệu theo xã
    sub = df[df["ten_xa"] == xa_name].sort_values("date")
    if sub.empty:
        return {"error": f"Không có dữ liệu NDVI cho xã {xa_name}"}

    ndvi_vals = sub["ndvi"].values.reshape(-1, 1)

    if len(ndvi_vals) < SEQUENCE:
        return {"error": f"Không đủ dữ liệu NDVI để dự báo cho xã {xa_name}"}

    # Lấy 10 bước cuối
    scaled = scaler.transform(ndvi_vals).flatten()
    last_seq = scaled[-SEQUENCE:]

    # Dự báo nhiều bước
    preds_real = predict_next_n_steps(model, scaler, last_seq, n_steps)

    last_date = sub["date"].max()
    future_dates = [
        last_date + pd.Timedelta(days=3 * i)
        for i in range(1, n_steps + 1)
    ]

    results = []
    for step, (d, v) in enumerate(zip(future_dates, preds_real), start=1):
        results.append({
            "ten_xa": xa_name,
            "step": step,
            "date": d,
            "predicted_ndvi": v
        })

    return results


def ndvi_get_history(xa, n=50):
    df = preprocess_ndvi()   # GIỜ LẤY TỪ MONGO
    df = df[df["ten_xa"] == xa].sort_values("date")

    if df.empty:
        return []

    return [
        {"date": str(row.date.date()), "value": float(row.ndvi)}
        for _, row in df.tail(n).iterrows()
    ]


def ndvi_history_with_forecast(xa, n_steps=7):
    history = ndvi_get_history(xa)
    forecast_raw = predict_ndvi_by_xa(xa, n_steps)

    if isinstance(forecast_raw, dict) and "error" in forecast_raw:
        return forecast_raw

    forecast = [
        {"date": str(item["date"].date()), "value": float(item["predicted_ndvi"])}
        for item in forecast_raw
    ]

    return {
        "xa": xa,
        "history": history,
        "forecast": forecast
    }
