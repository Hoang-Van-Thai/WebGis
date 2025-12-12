# app/services/lst_fetcher.py
import ee
import pandas as pd
import numpy as np
from datetime import datetime
import time

# SERVICE_ACCOUNT = 'gee-auto-export@vigilant-design-403812.iam.gserviceaccount.com'
# KEY_FILE = 'service_account/gee-auto-export.json'

# credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE)
# ee.Initialize(credentials, project='vigilant-design-403812')
from app.services.gee_init import init_gee

init_gee()
TINH_THANH = 'projects/vigilant-design-403812/assets/tinhthanh'
PHUONG_XA  = 'projects/vigilant-design-403812/assets/phuongxa'
TEN_TPHCM  = 'TP. Hồ Chí Minh'

tinhThanh = ee.FeatureCollection(TINH_THANH)
phuongXa  = ee.FeatureCollection(PHUONG_XA)

regionsToSample = phuongXa.filter(ee.Filter.eq('ten_tinh', TEN_TPHCM))
ROI             = tinhThanh.filter(ee.Filter.eq('ten_tinh', TEN_TPHCM)).union().geometry()

# def get_lst_weekly():
#     startDate = ee.Date('2000-01-01')
#     endDate = ee.Date(datetime.utcnow().strftime('%Y-%m-%d'))
def get_lst_weekly(start_date):
    startDate = ee.Date(start_date)
    endDate = ee.Date(datetime.utcnow().strftime('%Y-%m-%d'))

    lstDaily = (ee.ImageCollection("MODIS/061/MOD11A1")
        .filterDate(startDate, endDate)
        .select("LST_Day_1km")
        .map(lambda img: img.multiply(0.02).rename("LST_K")
                .copyProperties(img, ["system:time_start"])))

    n_days = endDate.difference(startDate, "day")
    steps = ee.List.sequence(0, n_days.subtract(1), 7)

    rows_all = []
    lst_list = lstDaily.toList(lstDaily.size())

    date_labels = []
    for i in range(steps.size().getInfo()):
        d = startDate.advance(steps.get(i), "day")
        date_labels.append(d.format("YYYY-MM-dd").getInfo())

    for idx in range(len(date_labels)):
        date_str = date_labels[idx]
        start = startDate.advance(steps.get(idx), "day")
        end   = start.advance(7, "day")

        img = lstDaily.filterDate(start, end).mean()
        if img.bandNames().size().getInfo() == 0:
            for f in regionsToSample.getInfo()["features"]:
                rows_all.append({
                    'ten_xa': f["properties"]["ten_xa"],
                    'ma_xa' : f["properties"]["ma_xa"],
                    'date'  : date_str,
                    'LST_K' : np.nan
                })
            continue

        reduced = img.reduceRegions(
            collection=regionsToSample,
            reducer=ee.Reducer.mean(),
            scale=1000
        ).getInfo()["features"]

        for f in reduced:
            p = f["properties"]
            rows_all.append({
                "ten_xa": p["ten_xa"],
                "ma_xa" : p["ma_xa"],
                "date"  : date_str,
                "LST_K" : p.get("mean")
            })

        time.sleep(0.3)

    df = pd.DataFrame(rows_all)
    return df
