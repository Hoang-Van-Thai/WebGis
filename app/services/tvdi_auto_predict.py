#
# # app/services/tvdi_auto_predict.py
# import numpy as np
# import pandas as pd
# from app.services.tvdi_service import model, scalers, WINDOW_SIZE
#
# CSV_PATH = "tvdi_tphcm_per_xa_3cot.csv"
#
# def auto_predict_tvdi(xa_name):
#     # Đọc dữ liệu đã được cập nhật weekly
#     df = pd.read_csv(CSV_PATH)
#     df = df[df["ten_xa"] == xa_name].sort_values("date").reset_index(drop=True)
#
#     if df.empty:
#         return {"error": f"Không có dữ liệu TVDI cho xã {xa_name}"}
#
#     df["date"] = pd.to_datetime(df["date"])
#     df = df.set_index("date").asfreq("MS")        # đảm bảo monthly
#     df["ten_xa"] = xa_name
#
#     df["mean"] = df["tvdi"].interpolate(method="time")
#     df["mean"] = df["mean"].rolling(window=3, min_periods=1).mean()
#
#     scaler = scalers.get(xa_name)
#     if scaler is None:
#         return {"error": f"Không tìm thấy scaler cho xã {xa_name}"}
#
#     df["mean_scaled"] = scaler.transform(df[["mean"]])
#
#     df["month"] = df.index.month
#     df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
#     df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
#
#     df["year"] = df.index.year
#     df["year_scaled"] = (df["year"] - df["year"].min()) / (df["year"].max() - df["year"].min())
#
#     if len(df) < WINDOW_SIZE:
#         return {"error": f"Không đủ dữ liệu, cần tối thiểu {WINDOW_SIZE} tháng"}
#
#     seq = df[["mean_scaled", "month_sin", "month_cos", "year_scaled"]].values[-WINDOW_SIZE:]
#     seq = seq.reshape(1, WINDOW_SIZE, 4)
#
#     pred_scaled = model.predict(seq)[0]
#     pred_real = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
#
#     return {
#         "xa": xa_name,
#         "history_months": df.index.strftime("%Y-%m").tolist(),
#         "prediction_scaled": pred_scaled.tolist(),
#         "prediction_real": pred_real.tolist()
#     }
# def tvdi_history_with_forecast(xa):
#     history = tvdi_get_history(xa)
#     forecast_raw = auto_predict_tvdi(xa)
#
#     if "error" in forecast_raw:
#         return forecast_raw
#
#     history_months = forecast_raw["history_months"]
#     pred = forecast_raw["prediction_real"]
#
#     last_year, last_month = map(int, history_months[-1].split("-"))
#
#     forecast = []
#     for v in pred:
#         last_month += 1
#         if last_month > 12:
#             last_month = 1
#             last_year += 1
#
#         forecast.append({
#             "date": f"{last_year}-{str(last_month).zfill(2)}-01",
#             "value": float(v)
#         })
#
#     return {
#         "xa": xa,
#         "history": history,
#         "forecast": forecast
#     }
# def tvdi_get_history(xa, n=50):
#     df = pd.read_csv("tvdi_tphcm_per_xa_3cot.csv")
#     df = df[df["ten_xa"] == xa].sort_values("date")
#
#     if df.empty:
#         return []
#
#     df["date"] = pd.to_datetime(df["date"])
#
#     return [
#         {"date": str(row.date.date()), "value": float(row.tvdi)}
#         for _, row in df.tail(n).iterrows()
#     ]
# app/services/tvdi_auto_predict.py

import numpy as np
import pandas as pd

from app.services.tvdi_service import model, scalers, WINDOW_SIZE
from app.db.mongo import tvdi_col   # DÙNG MONGO, KHÔNG DÙNG CSV NỮA


def _load_tvdi_df_from_mongo(xa_name: str) -> pd.DataFrame:
    """
    Lấy TVDI theo xã từ Mongo, sort theo date, đảm bảo kiểu dữ liệu chuẩn.
    Trả về DataFrame có cột: ten_xa, date, tvdi
    """
    docs = list(
        tvdi_col.find({"ten_xa": xa_name}).sort("date", 1)
    )

    if not docs:
        return pd.DataFrame(columns=["ten_xa", "date", "tvdi"])

    df = pd.DataFrame(docs)

    # Chuẩn cột date
    df["date"] = pd.to_datetime(df["date"])

    # Đảm bảo có cột tvdi
    if "tvdi" not in df.columns:
        raise ValueError("Không tìm thấy cột 'tvdi' trong collection tvdi_history")

    df = df[["ten_xa", "date", "tvdi"]].sort_values("date")
    return df


def auto_predict_tvdi(xa_name: str):
    # Đọc dữ liệu TVDI theo xã từ Mongo
    df = _load_tvdi_df_from_mongo(xa_name)

    if df.empty:
        return {"error": f"Không có dữ liệu TVDI cho xã {xa_name}"}

    # Đảm bảo index theo tháng (MS = Month Start)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").asfreq("MS")
    df["ten_xa"] = xa_name

    # Nội suy + làm mượt (rolling 3 tháng) giống code cũ
    df["mean"] = df["tvdi"].interpolate(method="time")
    df["mean"] = df["mean"].rolling(window=3, min_periods=1).mean()

    # Lấy scaler theo xã
    scaler = scalers.get(xa_name)
    if scaler is None:
        return {"error": f"Không tìm thấy scaler cho xã {xa_name}"}

    # Scale chỉ cột mean
    df["mean_scaled"] = scaler.transform(df[["mean"]])

    # Feature engineering (month_sin, month_cos, year_scaled)
    df["month"] = df.index.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    df["year"] = df.index.year
    df["year_scaled"] = (df["year"] - df["year"].min()) / (
        df["year"].max() - df["year"].min()
    )

    if len(df) < WINDOW_SIZE:
        return {"error": f"Không đủ dữ liệu, cần tối thiểu {WINDOW_SIZE} tháng"}

    seq = df[["mean_scaled", "month_sin", "month_cos", "year_scaled"]].values[-WINDOW_SIZE:]
    seq = seq.reshape(1, WINDOW_SIZE, 4)

    pred_scaled = model.predict(seq)[0]        # shape (3,)
    pred_real = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()

    return {
        "xa": xa_name,
        "history_months": df.index.strftime("%Y-%m").tolist(),
        "prediction_scaled": pred_scaled.tolist(),
        "prediction_real": pred_real.tolist(),
    }


def tvdi_get_history(xa: str, n: int = 50):
    df = _load_tvdi_df_from_mongo(xa)

    if df.empty:
        return []

    df = df.sort_values("date")

    return [
        {"date": str(row.date.date()), "value": float(row.tvdi)}
        for _, row in df.tail(n).iterrows()
    ]


def tvdi_history_with_forecast(xa: str):
    history = tvdi_get_history(xa)
    forecast_raw = auto_predict_tvdi(xa)

    if isinstance(forecast_raw, dict) and "error" in forecast_raw:
        return forecast_raw

    history_months = forecast_raw["history_months"]
    pred = forecast_raw["prediction_real"]

    # Lấy tháng cuối trong history_months, rồi cộng dần 3 bước
    last_year, last_month = map(int, history_months[-1].split("-"))

    forecast = []
    for v in pred:
        last_month += 1
        if last_month > 12:
            last_month = 1
            last_year += 1

        forecast.append(
            {
                "date": f"{last_year}-{str(last_month).zfill(2)}-01",
                "value": float(v),
            }
        )

    return {
        "xa": xa,
        "history": history,
        "forecast": forecast,
    }
