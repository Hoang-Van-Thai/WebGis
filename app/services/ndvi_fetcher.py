# app/services/ndvi_fetcher.py
# KEY_FILE = "service_account/gee-auto-export.json"

import ee
import pandas as pd
from datetime import datetime
import time
import math

# SERVICE_ACCOUNT = "gee-auto-export@vigilant-design-403812.iam.gserviceaccount.com"
# # KEY_FILE = "D:/API/service_account/gee-auto-export.json"
# KEY_FILE = "service_account/gee-auto-export.json"
# ee.Initialize(ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE))
from app.services.gee_init import init_gee

init_gee()
TINH_THANH = "projects/vigilant-design-403812/assets/tinhthanh"
PHUONG_XA  = "projects/vigilant-design-403812/assets/phuongxa"
TEN_TPHCM  = "TP. Hồ Chí Minh"

tinh = ee.FeatureCollection(TINH_THANH)
px   = ee.FeatureCollection(PHUONG_XA)

regions = px.filter(ee.Filter.eq("ten_tinh", TEN_TPHCM))
tinh_geom = tinh.filter(ee.Filter.eq("ten_tinh", TEN_TPHCM)).union().geometry()


def add_ndvi(img):
    return img.addBands(img.normalizedDifference(["B8", "B4"]).rename("ndvi"))


def fetch_fc_in_batches(fc, batch_size=1500):
    total = fc.size().getInfo()
    rows = []
    num_batches = math.ceil(total / batch_size)

    for i in range(num_batches):
        offset = i * batch_size
        size = min(batch_size, total - offset)

        print(f"Batch {i+1}/{num_batches} offset={offset} size={size}")

        batch = fc.toList(size, offset).getInfo()
        for f in batch:
            rows.append(f["properties"])

        time.sleep(1)

    return pd.DataFrame(rows)


def get_ndvi(start_date, end_date):
    print(f"NDVI {start_date} → {end_date}")

    col = (
        ee.ImageCollection("NASA/HLS/HLSS30/v002")
        .filterDate(start_date, end_date)
        .filterBounds(tinh_geom)
        .map(add_ndvi)
    )

    def compute(image):
        date = ee.Date(image.get("system:time_start")).format("YYYYMMdd")

        reduced = image.select("ndvi").reduceRegions(
            collection=regions,
            reducer=ee.Reducer.mean(),
            scale=30
        )

        def fix(f):
            return f.set({
                "date": date,
                "ten_xa": f.get("ten_xa"),
                "ndvi": f.get("mean")
            })

        return reduced.map(fix)

    fc = col.map(compute).flatten()
    fc = fc.filter(ee.Filter.notNull(["ndvi"]))

    df = fetch_fc_in_batches(fc)

    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby(["ten_xa", "date"])["ndvi"].mean().reset_index()
    df = df.sort_values(["ten_xa", "date"])

    return df


def get_ndvi_last_5_months():
    end = datetime.utcnow()
    start = end - pd.DateOffset(months=2)
    return get_ndvi(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
