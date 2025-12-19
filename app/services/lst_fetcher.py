
# app/services/lst_fetcher.py
import ee
import pandas as pd
import numpy as np
from datetime import datetime
import time

from app.services.gee_init import init_gee

init_gee()
TINH_THANH = 'projects/vigilant-design-403812/assets/tinhthanh'
PHUONG_XA  = 'projects/vigilant-design-403812/assets/phuongxa'
TEN_TPHCM  = 'TP. Hồ Chí Minh'

tinhThanh = ee.FeatureCollection(TINH_THANH)
phuongXa  = ee.FeatureCollection(PHUONG_XA)

regionsToSample = phuongXa.filter(ee.Filter.eq('ten_tinh', TEN_TPHCM))
ROI             = tinhThanh.filter(ee.Filter.eq('ten_tinh', TEN_TPHCM)).union().geometry()


def get_lst_weekly(start_date):
    startDate = ee.Date(start_date)
    endDate = ee.Date(datetime.utcnow().strftime('%Y-%m-%d'))

    lstDaily = (ee.ImageCollection("MODIS/061/MOD11A1")
        .filterDate(startDate, endDate)
        .select("LST_Day_1km")
        .map(lambda img: img.multiply(0.02)
                      .rename("LST_K")
                      .copyProperties(img, ["system:time_start"]))
    )

    n_days = endDate.difference(startDate, "day")
    steps = ee.List.sequence(0, n_days.subtract(1), 7)

    rows_all = []

    # tạo list label ngày theo step
    date_labels = []
    for i in range(steps.size().getInfo()):
        d = startDate.advance(steps.get(i), "day")
        date_labels.append(d.format("YYYY-MM-dd").getInfo())

    for idx in range(len(date_labels)):
        date_str = date_labels[idx]
        start = startDate.advance(steps.get(idx), "day")
        end   = start.advance(7, "day")

        # (1) check số ảnh trong tuần
        ic_week = lstDaily.filterDate(start, end)
        ic_count = ic_week.size().getInfo()
        if ic_count == 0:
            print(f"[LST][{date_str}] No images in this week -> skip")
            continue

        # (2) ảnh tuần
        img = ic_week.mean().rename("LST_K")

        # (3) map từng xã + reduceRegion(bestEffort=True)
        def per_feature(f):
            stat = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=f.geometry(),
                scale=1000,          # bạn có thể thử 2000 nếu vẫn null
                bestEffort=True,
                maxPixels=1e13
            )
            val = stat.get("LST_K")
            return f.set({"mean": val})

        reduced_fc = regionsToSample.map(per_feature)
        data = reduced_fc.getInfo()["features"]

        # (4) build rows, skip null mean
        skipped = 0
        kept = 0
        for f in data:
            p = f["properties"]
            val = p.get("mean")

            if val is None:
                skipped += 1
                # log nhẹ thôi (nếu muốn log chi tiết thì mở dòng dưới)
                # print(f"[LST][{date_str}] SKIP NULL mean | ten_xa={p.get('ten_xa')} ma_xa={p.get('ma_xa')}")
                continue

            kept += 1
            rows_all.append({
                "ten_xa": p.get("ten_xa"),
                "ma_xa":  p.get("ma_xa"),
                "date":   date_str,
                "LST_K":  val
            })

        print(f"[LST][{date_str}] icCount={ic_count} | kept={kept} | skipped_null={skipped}")

        time.sleep(0.3)

    df = pd.DataFrame(rows_all)
    return df
