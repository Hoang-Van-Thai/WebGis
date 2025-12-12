#
# import pandas as pd
# from datetime import datetime
# from app.services.ndvi_fetcher import get_ndvi
#
# CSV_FILE = "ndvi_latest.csv"
#
# def update_ndvi():
#     print("Fetching NDVI incremental...")
#
#     try:
#         old_df = pd.read_csv(CSV_FILE)
#         old_df["date"] = pd.to_datetime(old_df["date"])
#         latest_date = old_df["date"].max()
#         start_date = (latest_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
#         print("Da co du lieu toi:", latest_date.date())
#         print("Bat dau crawl tu:", start_date)
#
#     except Exception as e:
#         print("Khong doc duoc file cu, chay tu dau. Loi:", e)
#         old_df = pd.DataFrame(columns=["ten_xa", "date", "ndvi"])
#         start_date = "2000-01-01"
#         print("Bat dau crawl tu:", start_date)
#
#     end_date = datetime.utcnow().strftime("%Y-%m-%d")
#
#     if pd.to_datetime(start_date) > pd.to_datetime(end_date):
#         print("Du lieu da cap nhat toi ngay moi nhat, khong co gi moi.")
#         return
#
#     new_df = get_ndvi(start_date, end_date)
#
#     if new_df is None or len(new_df) == 0:
#         print("Khong co NDVI moi tu GEE.")
#         return
#
#     df = pd.concat([old_df, new_df], ignore_index=True)
#
#     df["date"] = pd.to_datetime(df["date"])
#     df = df.drop_duplicates(subset=["ten_xa", "date"])
#     df = df.sort_values(["ten_xa", "date"])
#
#     df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
#     print("UPDATED:", CSV_FILE, "Tong so dong:", len(df))
#
#
# if __name__ == "__main__":
#     update_ndvi()
# app/services/update_ndvi_3d.py

import pandas as pd
from datetime import datetime
from pymongo import UpdateOne

from app.services.ndvi_fetcher import get_ndvi
from app.db.mongo import ndvi_col


def update_ndvi():
    print("Fetching NDVI incremental → MongoDB ...")

    # 1) Lấy ngày mới nhất đã có trong Mongo
    last_doc = ndvi_col.find_one(sort=[("date", -1)])
    if last_doc:
        latest_date = last_doc["date"]
        # có thể +1 ngày nếu muốn, nhưng để nguyên cũng được
        start_date = latest_date.strftime("%Y-%m-%d")
        print("Đã có NDVI tới:", latest_date.date())
    else:
        start_date = "2000-01-01"
        print("Chưa có dữ liệu NDVI, bắt đầu từ:", start_date)

    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Nếu start_date > end_date thì thôi
    if pd.to_datetime(start_date) > pd.to_datetime(end_date):
        print("Dữ liệu NDVI đã cập nhật tới ngày mới nhất, không có gì mới.")
        return

    # 2) Lấy NDVI mới từ GEE
    new_df = get_ndvi(start_date, end_date)

    if new_df is None or len(new_df) == 0:
        print("Không có NDVI mới từ GEE.")
        return

    new_df["date"] = pd.to_datetime(new_df["date"])

    # 3) Chuẩn bị bulk upsert vào Mongo
    ops = []
    for _, row in new_df.iterrows():
        doc = {
            "ten_xa": row["ten_xa"],
            "date": row["date"].to_pydatetime(),
            "ndvi": float(row["ndvi"]),
            "source": "HLS_HLSS30_v002",
        }

        ops.append(
            UpdateOne(
                {"ten_xa": doc["ten_xa"], "date": doc["date"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )
        )

    if ops:
        result = ndvi_col.bulk_write(ops, ordered=False)
        print(
            "Upsert NDVI xong. matched:",
            result.matched_count,
            "upserted:",
            len(result.upserted_ids),
        )


if __name__ == "__main__":
    update_ndvi()
