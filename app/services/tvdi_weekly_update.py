#
# # app/services/tvdi_weekly_update.py
# import pandas as pd
# from datetime import datetime
# from app.services.tvdi_fetcher import get_tvdi
#
# CSV_PATH = "tvdi_tphcm_per_xa_3cot.csv"
#
#
# def update_tvdi_weekly():
#     print("Fetching TVDI incremental...")
#
#     try:
#         old_df = pd.read_csv(CSV_PATH)
#         old_df["date"] = pd.to_datetime(old_df["date"])
#         latest_date = old_df["date"].max()
#         start_date = (latest_date + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
#         print("Da co du lieu toi:", latest_date.date())
#         print("Bat dau crawl tu:", start_date)
#     except FileNotFoundError:
#         old_df = pd.DataFrame(columns=["ten_xa", "date", "tvdi"])
#         start_date = "2000-01-01"
#         print("Khong tim thay file cu, bat dau tu:", start_date)
#
#     end_date = datetime.utcnow().strftime("%Y-%m-%d")
#
#     if pd.to_datetime(start_date) > pd.to_datetime(end_date):
#         print("Du lieu da cap nhat toi ngay moi nhat, khong co gi moi.")
#         return
#
#     new_df = get_tvdi(start_date, end_date)
#
#     if new_df is None or len(new_df) == 0:
#         print("Khong co TVDI moi trong khoang nay.")
#         return
#
#     new_df["date"] = pd.to_datetime(new_df["date"])
#
#     df = pd.concat([old_df, new_df], ignore_index=True)
#     df = df.drop_duplicates(subset=["ten_xa", "date"])
#     df = df.sort_values(["ten_xa", "date"])
#
#     df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
#     print("UPDATED:", CSV_PATH, "Tong so dong:", len(df))
#
#
# if __name__ == "__main__":
#     update_tvdi_weekly()
# app/services/tvdi_weekly_update.py

import pandas as pd
from datetime import datetime
from pymongo import UpdateOne

from app.services.tvdi_fetcher import get_tvdi
from app.db.mongo import tvdi_col


def update_tvdi_weekly():
    """
    Lấy TVDI mới từ GEE và upsert vào MongoDB (collection tvdi_history).
    Không dùng CSV nữa.
    """
    print("Fetching TVDI incremental → MongoDB ...")

    # 1) Lấy ngày mới nhất đã có trong Mongo
    last_doc = tvdi_col.find_one(sort=[("date", -1)])
    if last_doc:
        latest_date = last_doc["date"]
        start_date = latest_date.strftime("%Y-%m-%d")
        print("Đã có TVDI tới:", latest_date.date())
    else:
        start_date = "2000-01-01"
        print("Chưa có dữ liệu TVDI, bắt đầu từ:", start_date)

    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    if pd.to_datetime(start_date) > pd.to_datetime(end_date):
        print("Dữ liệu TVDI đã cập nhật tới ngày mới nhất, không có gì mới.")
        return

    # 2) Lấy TVDI từ GEE
    new_df = get_tvdi(start_date, end_date)

    if new_df is None or len(new_df) == 0:
        print("Không có TVDI mới trong khoảng này.")
        return

    new_df["date"] = pd.to_datetime(new_df["date"])

    # 3) Chuẩn bị bulk upsert vào Mongo
    ops = []
    for _, row in new_df.iterrows():
        doc = {
            "ten_xa": row["ten_xa"],
            "date": row["date"].to_pydatetime(),
            "tvdi": float(row["tvdi"]) if pd.notna(row["tvdi"]) else None,
            "source": "MODIS_TVDI_monthly",
        }

        ops.append(
            UpdateOne(
                {"ten_xa": doc["ten_xa"], "date": doc["date"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )
        )

    if ops:
        result = tvdi_col.bulk_write(ops, ordered=False)
        print(
            "Upsert TVDI xong. matched:",
            result.matched_count,
            "upserted:",
            len(result.upserted_ids),
        )


if __name__ == "__main__":
    update_tvdi_weekly()
