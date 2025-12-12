# # app/db/mongo.py
# import os
# from urllib.parse import quote_plus
# from pymongo import MongoClient
#
# USERNAME = quote_plus(os.getenv("MONGO_USER", "thai"))
# PASSWORD = quote_plus(os.getenv("MONGO_PASS", "yXMm7z.L33Ly@hk"))
#
# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     f"mongodb+srv://{USERNAME}:{PASSWORD}"
#     "@cluster0.hbzcx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# )
#
# DB_NAME = "webgis"
#
# client = MongoClient(MONGO_URI)
# db = client[DB_NAME]
#
# ndvi_col = db["ndvi_history"]
# lst_col = db["lst_history"]
# tvdi_col = db["tvdi_history"]
# xa_col = db["xa_list"]
# app/db/mongo.py
import os
from urllib.parse import quote_plus
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Bắt buộc phải có trong .env
RAW_USERNAME = os.getenv("MONGO_USER")
RAW_PASSWORD = os.getenv("MONGO_PASS")
DB_NAME      = os.getenv("MONGO_DB_NAME")

if not RAW_USERNAME or not RAW_PASSWORD or not DB_NAME:
    raise RuntimeError("Missing MONGO_USER, MONGO_PASS or MONGO_DB_NAME in .env")

# Encode để tránh lỗi InvalidURI
USERNAME = quote_plus(RAW_USERNAME)
PASSWORD = quote_plus(RAW_PASSWORD)

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    MONGO_URI = (
        f"mongodb+srv://{USERNAME}:{PASSWORD}"
        "@cluster0.hbzcx.mongodb.net/"
        f"{DB_NAME}?retryWrites=true&w=majority&appName=Cluster0"
    )

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

ndvi_col = db["ndvi_history"]
lst_col  = db["lst_history"]
tvdi_col = db["tvdi_history"]
xa_col   = db["xa_list"]
