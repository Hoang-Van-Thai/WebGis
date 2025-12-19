
import ee
import pandas as pd
from datetime import datetime

from app.services.gee_init import init_gee

init_gee()
PHUONG_XA_ASSET_ID = "projects/vigilant-design-403812/assets/phuongxa"
TINH_THANH_ASSET_ID = "projects/vigilant-design-403812/assets/tinhthanh"
TEN_TPHCM = "TP. Hồ Chí Minh"


def get_tvdi(start_date: str, end_date: str) -> pd.DataFrame:
    phuongXa = ee.FeatureCollection(PHUONG_XA_ASSET_ID)
    tinhThanh = ee.FeatureCollection(TINH_THANH_ASSET_ID)

    regions = phuongXa.filter(ee.Filter.eq("ten_tinh", TEN_TPHCM))
    ROI = tinhThanh.filter(ee.Filter.eq("ten_tinh", TEN_TPHCM)).union().geometry()

    startDate = ee.Date(start_date)
    endDate = ee.Date(end_date)

    ndvi = (
        ee.ImageCollection("MODIS/061/MOD13A2")
        .filterDate(startDate, endDate)
        .select("NDVI")
        .map(
            lambda img: img.multiply(0.0001)
            .rename("NDVI")
            .copyProperties(img, ["system:time_start"])
        )
    )

    lst = (
        ee.ImageCollection("MODIS/061/MOD11A2")
        .filterDate(startDate, endDate)
        .select("LST_Day_1km")
        .map(
            lambda img: img.multiply(0.02)
            .subtract(273.15)
            .rename("LST")
            .copyProperties(img, ["system:time_start"])
        )
    )

    n_months = endDate.difference(startDate, "month")
    months = ee.List.sequence(0, n_months.subtract(1))

    def monthly(m):
        m = ee.Number(m)
        s = startDate.advance(m, "month")
        e = s.advance(1, "month")
        img = (
            ndvi.filterDate(s, e)
            .mean()
            .addBands(lst.filterDate(s, e).mean())
            .set("system:time_start", s.millis())
            .set("date", s.format("YYYY-MM"))
        )
        return img

    monthlyIC = ee.ImageCollection(months.map(monthly))

    def calc(img):
        nd = img.select("NDVI")
        ls = img.select("LST")
        combined = nd.addBands(ls)

        stats = combined.reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=ROI,
            scale=1000,
            bestEffort=True,
            maxPixels=1e13,
        )

        lst_min = ee.Number(stats.get("LST_min"))
        lst_max = ee.Number(stats.get("LST_max"))

        tvdi = (
            ls.subtract(lst_min)
            .divide(lst_max.subtract(lst_min))
            .rename("TVDI")
        )

        return tvdi.set("date", img.get("date")).set(
            "system:time_start", img.get("system:time_start")
        )

    tvdiCollection = monthlyIC.map(calc)

    def reduce_by_xa(img):
        date_str = ee.Date(img.get("system:time_start")).format("YYYY-MM")
        reduced = img.reduceRegions(
            collection=regions,
            reducer=ee.Reducer.mean(),
            scale=1000,
        ).map(
            lambda f: f.set(
                {
                    "date": date_str,
                    "ten_xa": f.get("ten_xa"),
                    "tvdi": f.get("mean"),
                }
            )
        )
        return reduced

    tvdiAll = tvdiCollection.map(reduce_by_xa).flatten()
    tvdi_list = tvdiAll.getInfo()["features"]

    if not tvdi_list:
        return pd.DataFrame(columns=["ten_xa", "date", "tvdi"])

    df = pd.DataFrame([f["properties"] for f in tvdi_list])
    return df


def get_tvdi_last_20_months() -> pd.DataFrame:
    end = datetime.utcnow()
    start = end - pd.DateOffset(months=20)
    return get_tvdi(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
