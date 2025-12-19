
import pandas as pd
from datetime import datetime
from pymongo import UpdateOne

from app.services.lst_fetcher import get_lst_weekly
from app.db.mongo import lst_col


def update_lst_weekly_to_mongo():
    print("Fetching LST weekly → MongoDB ...")

    # 1) Lấy ngày mới nhất đã có trong Mongo
    last_doc = lst_col.find_one(sort=[("date", -1)])
    if last_doc:
        latest_date = last_doc["date"]
        start_date = latest_date.strftime("%Y-%m-%d")
        print("Đã có dữ liệu tới:", latest_date.date())
    else:
        start_date = "2000-01-01"
        print("Chưa có dữ liệu LST, bắt đầu từ:", start_date)

    # 2) Lấy dữ liệu weekly mới từ GEE
    new_df = get_lst_weekly(start_date)

    if new_df is None or len(new_df) == 0:
        print("Không có dữ liệu LST mới.")
        return

    new_df["date"] = pd.to_datetime(new_df["date"])

    # 3) Chuẩn bị bulk upsert vào Mongo
    ops = []
    for _, row in new_df.iterrows():

        doc = {
            "ten_xa": row["ten_xa"],
            "ma_xa": row.get("ma_xa"),
            "date": row["date"].to_pydatetime(),
            "lst_k": float(row["LST_K"]) if pd.notna(row["LST_K"]) else None,
            "source": "MODIS11A1_weekly_raw",
        }

        # Upsert theo (ten_xa, date)
        ops.append(
            UpdateOne(
                {"ten_xa": doc["ten_xa"], "date": doc["date"]},
                # {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                # {"$setOnInsert": {**doc, "created_at": datetime.utcnow()}},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},

        upsert=True,
            )
        )

    if ops:
        result = lst_col.bulk_write(ops, ordered=False)
        print(
            "Upsert LST xong. matched:",
            result.matched_count,
            "upserted:",
            len(result.upserted_ids),
        )


if __name__ == "__main__":
    update_lst_weekly_to_mongo()
