#
# import os
# from urllib.parse import quote_plus
# from datetime import datetime
#
# import pandas as pd
# from pymongo import MongoClient
# from pymongo.errors import CollectionInvalid
#
#
# # ==========================
# # 1. KẾT NỐI MONGODB ATLAS
# # ==========================
#
# USERNAME = quote_plus("thai")
# PASSWORD = quote_plus("yXMm7z.L33Ly@hk")
#
# MONGO_URI = (
#     f"mongodb+srv://{USERNAME}:{PASSWORD}"
#     "@cluster0.hbzcx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# )
#
# DB_NAME = "webgis"
#
#
# def get_client():
#     return MongoClient(MONGO_URI)
#
#
# client = get_client()
# db = client[DB_NAME]
#
# ndvi_col = db["ndvi_history"]
# lst_col = db["lst_history"]
# tvdi_col = db["tvdi_history"]
#
#
# # ==========================
# # 2. TẠO COLLECTION + INDEX
# # ==========================
#
# def create_collections_and_indexes():
#     for name in ["ndvi_history", "lst_history", "tvdi_history"]:
#         try:
#             db.create_collection(name)
#             print(f"Created collection: {name}")
#         except CollectionInvalid:
#             print(f"Collection already exists: {name}")
#
#     # NDVI: 1 doc / (ten_xa, date)
#     ndvi_col.create_index([("ten_xa", 1), ("date", 1)], unique=True)
#     ndvi_col.create_index([("date", 1)])
#     print("Indexes created for ndvi_history")
#
#     # LST: weekly theo xã
#     lst_col.create_index([("ten_xa", 1), ("date", 1)], unique=True)
#     lst_col.create_index([("date", 1)])
#     print("Indexes created for lst_history")
#
#     # TVDI: monthly theo xã
#     tvdi_col.create_index([("ten_xa", 1), ("date", 1)], unique=True)
#     tvdi_col.create_index([("date", 1)])
#     print("Indexes created for tvdi_history")
#
#
# # ==========================
# # 3. HÀM ĐỌC FILE (CSV / EXCEL)
# # ==========================
#
# def load_df(path: str) -> pd.DataFrame:
#     if not os.path.exists(path):
#         raise FileNotFoundError(f"Không tìm thấy file: {path}")
#
#     ext = os.path.splitext(path)[1].lower()
#     if ext in [".csv", ".txt"]:
#         df = pd.read_csv(path)
#     elif ext in [".xls", ".xlsx"]:
#         df = pd.read_excel(path)
#     else:
#         raise ValueError(f"Định dạng file không hỗ trợ: {ext}")
#
#     if "date" not in df.columns:
#         raise ValueError(f"File {path} không có cột 'date'")
#
#     df["date"] = pd.to_datetime(df["date"])
#     return df
#
#
# # ==========================
# # 4. IMPORT NDVI
# # ==========================
#
# NDVI_FILE = "ndvi_latest.csv"
#
#
# def import_ndvi():
#     print(f"\n=== Import NDVI from {NDVI_FILE} ===")
#     df = load_df(NDVI_FILE)
#
#     # Kỳ vọng cột: ten_xa, date, ndvi
#     missing = [c for c in ["ten_xa", "ndvi"] if c not in df.columns]
#     if missing:
#         raise ValueError(f"File NDVI thiếu cột: {missing}")
#
#     # Xoá dữ liệu cũ (nếu muốn incremental thì có thể sửa ở đây)
#     ndvi_col.delete_many({})
#     print("Đã xoá toàn bộ dữ liệu cũ trong ndvi_history")
#
#     docs = []
#     for _, row in df.iterrows():
#         docs.append(
#             {
#                 "ten_xa": row["ten_xa"],
#                 "date": row["date"].to_pydatetime(),
#                 "ndvi": float(row["ndvi"]),
#                 "source": "HLS_HLSS30_v002",
#                 "created_at": datetime.utcnow(),
#             }
#         )
#
#     if docs:
#         ndvi_col.insert_many(docs)
#         print("Inserted", len(docs), "NDVI records")
#
#
# # ==========================
# # 5. IMPORT LST WEEKLY
# # ==========================
#
# LST_FILE = "lst_weekly_interpolated.csv"
#
#
# def import_lst():
#     print(f"\n=== Import LST from {LST_FILE} ===")
#     df = load_df(LST_FILE)
#
#     # Kỳ vọng cột: ten_xa, date, LST_K
#     missing = [c for c in ["ten_xa", "LST_K"] if c not in df.columns]
#     if missing:
#         raise ValueError(f"File LST thiếu cột: {missing}")
#
#     lst_col.delete_many({})
#     print("Đã xoá toàn bộ dữ liệu cũ trong lst_history")
#
#     docs = []
#     for _, row in df.iterrows():
#         docs.append(
#             {
#                 "ten_xa": row["ten_xa"],
#                 "date": row["date"].to_pydatetime(),
#                 "lst_k": float(row["LST_K"]) if pd.notna(row["LST_K"]) else None,
#                 "source": "MODIS11A1_weekly_interpolated",
#                 "created_at": datetime.utcnow(),
#             }
#         )
#
#     if docs:
#         lst_col.insert_many(docs)
#         print("Inserted", len(docs), "LST records")
#
#
# # ==========================
# # 6. IMPORT TVDI
# # ==========================
#
# TVDI_FILE = "tvdi_tphcm_per_xa_3cot.csv"
#
#
# def import_tvdi():
#     print(f"\n=== Import TVDI from {TVDI_FILE} ===")
#     df = load_df(TVDI_FILE)
#
#     # Kỳ vọng cột: ten_xa, date, tvdi
#     missing = [c for c in ["ten_xa", "tvdi"] if c not in df.columns]
#     if missing:
#         raise ValueError(f"File TVDI thiếu cột: {missing}")
#
#     tvdi_col.delete_many({})
#     print("Đã xoá toàn bộ dữ liệu cũ trong tvdi_history")
#
#     docs = []
#     for _, row in df.iterrows():
#         docs.append(
#             {
#                 "ten_xa": row["ten_xa"],
#                 "date": row["date"].to_pydatetime(),
#                 "tvdi": float(row["tvdi"]),
#                 "source": "MODIS_TVDI_monthly",
#                 "created_at": datetime.utcnow(),
#             }
#         )
#
#     if docs:
#         tvdi_col.insert_many(docs)
#         print("Inserted", len(docs), "TVDI records")
#
#
# # ==========================
# # 7. MAIN
# # ==========================
#
# if __name__ == "__main__":
#     print("Kết nối MongoDB Atlas:", DB_NAME)
#     create_collections_and_indexes()
#
#     # Import từng loại dữ liệu
#     try:
#         import_ndvi()
#     except Exception as e:
#         print("Lỗi import NDVI:", e)
#
#     try:
#         import_lst()
#     except Exception as e:
#         print("Lỗi import LST:", e)
#
#     try:
#         import_tvdi()
#     except Exception as e:
#         print("Lỗi import TVDI:", e)
#
#     print("\n=== DONE ===")

# app/debug/show_last_15days.py

import pandas as pd
from app.db.mongo import ndvi_col, lst_col, tvdi_col


XA_NAME = "Côn Đảo"
N_DAYS = 15


def fetch_last_records(col, xa, value_key):
    """
    Lấy N_DAYS record mới nhất từ một collection Mongo.
    value_key: tên trường giá trị (ndvi / lst_k / tvdi)
    """

    docs = list(
        col.find({"ten_xa": xa}).sort("date", -1).limit(N_DAYS)
    )

    if not docs:
        return pd.DataFrame(columns=["date", value_key])

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", value_key]].sort_values("date")

    return df


if __name__ == "__main__":

    print(f"\n=== LST – last {N_DAYS} values for {XA_NAME} ===")
    lst_df = fetch_last_records(lst_col, XA_NAME, "lst_k")
    print(lst_df)

    print(f"\n=== NDVI – last {N_DAYS} values for {XA_NAME} ===")
    ndvi_df = fetch_last_records(ndvi_col, XA_NAME, "ndvi")
    print(ndvi_df)

    print(f"\n=== TVDI – last {N_DAYS} values for {XA_NAME} ===")
    tvdi_df = fetch_last_records(tvdi_col, XA_NAME, "tvdi")
    print(tvdi_df)
