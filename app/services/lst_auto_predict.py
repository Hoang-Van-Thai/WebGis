
import numpy as np
import pandas as pd

from app.services.lst_service import model, scalers
from app.db.mongo import lst_col


def _load_lst_df_from_mongo(xa: str) -> pd.DataFrame:

    docs = list(
        lst_col.find({"ten_xa": xa}).sort("date", 1)
    )

    if not docs:
        return pd.DataFrame(columns=["ten_xa", "date", "LST_K"])

    df = pd.DataFrame(docs)

    # Chuẩn cột date
    df["date"] = pd.to_datetime(df["date"])

    # Chuẩn cột LST_K
    if "LST_K" in df.columns:
        pass
    elif "lst_k" in df.columns:
        df.rename(columns={"lst_k": "LST_K"}, inplace=True)
    else:
        raise ValueError("Không tìm thấy cột LST_K hoặc lst_k trong Mongo cho LST")

    df = df[["ten_xa", "date", "LST_K"]].sort_values("date")

    # Nội suy theo thời gian cho LST_K
    df = df.set_index("date")
    df["LST_K"] = df["LST_K"].astype(float)
    df["LST_K"] = df["LST_K"].interpolate(method="time", limit_direction="both")
    df = df.reset_index()

    return df


def lst_predict_next_7_weeks(xa: str):
    # Đọc dữ liệu từ Mongo + nội suy
    df = _load_lst_df_from_mongo(xa)

    if len(df) < 12:
        return {"error": "Không đủ dữ liệu"}

    # Lấy scaler theo xã
    scaler = scalers.get(xa)
    if scaler is None:
        return {"error": "Không có scaler cho xã này"}

    # Scale chỉ LST_K
    df["LST_scaled"] = scaler.transform(df[["LST_K"]])

    # Feature engineering giống code cũ
    df["week"] = pd.to_datetime(df["date"]).dt.isocalendar().week.astype(int)
    df["week_sin"] = np.sin(2 * np.pi * df["week"] / 52)
    df["week_cos"] = np.cos(2 * np.pi * df["week"] / 52)

    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["year_scaled"] = (df["year"] - df["year"].min()) / (
        df["year"].max() - df["year"].min()
    )
    print("\n=== 12 bước dữ liệu được dùng để dự đoán ===")
    for _, row in df.tail(12).iterrows():
        print(f"{row['date'].date()}  ->  LST_K = {row['LST_K']:.3f}")

    # Lấy 12 bước cuối làm input
    last_seq = df[["LST_scaled", "week_sin", "week_cos", "year_scaled"]].tail(12).values
    seq = last_seq.copy()

    predictions_scaled = []
    predictions_real = []

    for _ in range(7):
        X = seq.reshape(1, 12, 4)

        pred_scaled = model.predict(X)[0][0]
        pred_real = scaler.inverse_transform([[pred_scaled]])[0][0]

        predictions_scaled.append(float(pred_scaled))
        predictions_real.append(float(pred_real))

        # Update sequence: shift trái + thêm giá trị mới
        new_feature_vector = seq[-1].copy()
        new_feature_vector[0] = pred_scaled  # Update LST_scaled

        seq = np.vstack([seq[1:], new_feature_vector])

    return {
        "xa": xa,
        "last_date": str(df["date"].max().date()),
        "pred_scaled": predictions_scaled,
        "pred_LST_K": predictions_real,
    }


def lst_get_history(xa: str, n: int = 50):
    df = _load_lst_df_from_mongo(xa)

    if df.empty:
        return []

    df = df.sort_values("date")

    return [
        {"date": str(row.date.date()), "value": float(row.LST_K)}
        for _, row in df.tail(n).iterrows()
    ]


def lst_history_with_forecast(xa: str):
    history = lst_get_history(xa)
    forecast_raw = lst_predict_next_7_weeks(xa)

    if isinstance(forecast_raw, dict) and "error" in forecast_raw:
        return forecast_raw

    last_date = pd.to_datetime(forecast_raw["last_date"])

    forecast = []
    for i, val in enumerate(forecast_raw["pred_LST_K"], start=1):
        d = last_date + pd.Timedelta(days=7 * i)
        forecast.append(
            {
                "date": str(d.date()),
                "value": float(val),
            }
        )

    return {
        "xa": xa,
        "history": history,
        "forecast": forecast,
    }
