# # check_lst_trend_hcm.py
# import ee
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# from datetime import datetime
#
# from app.services.gee_init import init_gee
#
# # =========================
# # CONFIG
# # =========================
# TINH_THANH = "projects/vigilant-design-403812/assets/tinhthanh"
# TEN_TPHCM  = "TP. Hồ Chí Minh"
#
# START_DATE = "2018-01-01"  # đổi theo dataset bạn muốn kiểm tra
# END_DATE   = None          # None = lấy đến hôm nay (UTC)
#
# STEP_DAYS  = 7
#
# OUT_CSV    = "hcm_lst_weekly_mean.csv"
# OUT_PNG    = "hcm_lst_weekly_mean.png"
#
# # =========================
# # HELPERS
# # =========================
# def ee_date_str(d: ee.Date) -> str:
#     return d.format("YYYY-MM-dd").getInfo()
#
# def to_datetime(s: str) -> pd.Timestamp:
#     return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
#
# def linear_trend_slope_degC_per_year(df: pd.DataFrame) -> float:
#     """
#     Fit y = a*x + b with x in years, return slope a (°C/year).
#     """
#     # x as fractional year
#     x = df["date_dt"].map(lambda t: t.toordinal()).to_numpy(dtype=float)
#     # convert ordinal days -> years (approx)
#     x_years = (x - x.min()) / 365.25
#     y = df["lst_c"].to_numpy(dtype=float)
#
#     # polyfit degree 1
#     a, b = np.polyfit(x_years, y, 1)
#     return float(a)
#
# def main():
#     init_gee()
#
#     tinhThanh = ee.FeatureCollection(TINH_THANH)
#     roi = tinhThanh.filter(ee.Filter.eq("ten_tinh", TEN_TPHCM)).union().geometry()
#
#     start = ee.Date(START_DATE)
#     end = ee.Date(datetime.utcnow().strftime("%Y-%m-%d")) if END_DATE is None else ee.Date(END_DATE)
#
#     # MODIS LST Day 1km, scale factor 0.02, Kelvin
#     ic = (
#         ee.ImageCollection("MODIS/061/MOD11A1")
#         .filterDate(start, end)
#         .select("LST_Day_1km")
#         .map(lambda img: img.multiply(0.02).rename("LST_K").copyProperties(img, ["system:time_start"]))
#     )
#
#     n_days = end.difference(start, "day")
#     steps = ee.List.sequence(0, n_days.subtract(1), STEP_DAYS)
#
#     # build weekly rows
#     rows = []
#     steps_list = steps.getInfo()  # list of offsets
#     print(f"Total steps (weekly windows): {len(steps_list)}")
#
#     for off in steps_list:
#         w_start = start.advance(off, "day")
#         w_end = w_start.advance(STEP_DAYS, "day")
#         label = ee_date_str(w_start)
#
#         ic_week = ic.filterDate(w_start, w_end)
#         count = ic_week.size().getInfo()
#         if count == 0:
#             print(f"[{label}] No images -> skip")
#             continue
#
#         img_week = ic_week.mean().rename("LST_K")
#
#         stat = img_week.reduceRegion(
#             reducer=ee.Reducer.mean(),
#             geometry=roi,
#             scale=1000,
#             bestEffort=True,
#             maxPixels=1e13,
#         )
#
#         val_k = stat.get("LST_K").getInfo()
#         if val_k is None:
#             print(f"[{label}] ROI mean is NULL -> skip")
#             continue
#
#         val_c = float(val_k) - 273.15
#         rows.append({"date": label, "ic_count": int(count), "lst_k": float(val_k), "lst_c": val_c})
#         print(f"[{label}] icCount={count} | mean={val_c:.2f} °C")
#
#     if not rows:
#         raise RuntimeError("Không lấy được dữ liệu weekly mean cho TP.HCM. Kiểm tra ROI / asset / quyền GEE.")
#
#     df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
#     df["date_dt"] = df["date"].apply(to_datetime)
#
#     # Trend slope
#     slope = linear_trend_slope_degC_per_year(df)
#
#     # Save CSV
#     df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
#     print("Saved:", OUT_CSV)
#
#     # Plot
#     plt.figure(figsize=(12, 5), dpi=160)
#     plt.plot(df["date_dt"], df["lst_c"])
#     plt.title(f"HCMC MODIS LST weekly mean (7-day) | slope ≈ {slope:.3f} °C/year")
#     plt.xlabel("Date")
#     plt.ylabel("LST (°C)")
#     plt.tight_layout()
#     plt.savefig(OUT_PNG)
#     plt.close()
#     print("Saved:", OUT_PNG)
#
#     # Quick interpretation
#     if slope > 0:
#         print(f"Trend: tăng (slope ≈ +{slope:.3f} °C/năm)")
#     elif slope < 0:
#         print(f"Trend: giảm (slope ≈ {slope:.3f} °C/năm)")
#     else:
#         print("Trend: gần như phẳng (slope ≈ 0)")
#
# if __name__ == "__main__":
#     main()
# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
#
# CSV = "hcm_lst_weekly_mean.csv"
#
# df = pd.read_csv(CSV)
# df["date"] = pd.to_datetime(df["date"])
# df = df.dropna(subset=["lst_c"])
#
# # (khuyến nghị) bỏ các tuần thiếu ảnh
# df = df[df["ic_count"] >= 6]
#
# df["year"] = df["date"].dt.year
# yearly = df.groupby("year")["lst_c"].mean().reset_index()
#
# x = yearly["year"].to_numpy(dtype=float)
# y = yearly["lst_c"].to_numpy(dtype=float)
# a, b = np.polyfit(x, y, 1)   # °C / year
#
# print(yearly)
# print(f"Slope yearly mean: {a:.3f} °C/năm")
#
# plt.figure(figsize=(8,4), dpi=160)
# plt.plot(yearly["year"], yearly["lst_c"], marker="o")
# plt.title(f"HCMC yearly mean LST (from weekly) | slope ≈ {a:.3f} °C/year")
# plt.xlabel("Year")
# plt.ylabel("LST (°C)")
# plt.tight_layout()
# plt.savefig("hcm_lst_yearly_trend.png")
# plt.close()
# print("Saved: hcm_lst_yearly_trend.png")
import ee
import numpy as np
from datetime import datetime

from app.services.gee_init import init_gee

# =========================
# CONFIG
# =========================
TINH_THANH = "projects/vigilant-design-403812/assets/tinhthanh"
TEN_TPHCM  = "TP. Hồ Chí Minh"

START_DATE = "2018-01-01"
END_DATE   = None        # None = today
STEP_DAYS  = 7

# Chỉ giữ tuần có đủ ảnh
MIN_IC_COUNT = 6

# QC MODE
# "strict": QC_Day == 0
# "relaxed": QC_Day < 3
QC_MODE = "strict"

# =========================
def main():
    init_gee()

    tinhThanh = ee.FeatureCollection(TINH_THANH)
    roi = tinhThanh.filter(
        ee.Filter.eq("ten_tinh", TEN_TPHCM)
    ).union().geometry()

    start = ee.Date(START_DATE)
    end = ee.Date(datetime.utcnow().strftime("%Y-%m-%d")) if END_DATE is None else ee.Date(END_DATE)

    # -------------------------
    # Load MODIS + QC_Day
    # -------------------------
    ic_raw = (
        ee.ImageCollection("MODIS/061/MOD11A1")
        .filterDate(start, end)
        .select(["LST_Day_1km", "QC_Day"])
    )

    def apply_qc(img):
        qc = img.select("QC_Day")
        if QC_MODE == "strict":
            mask = qc.eq(0)
        else:
            mask = qc.lt(3)

        lst = (
            img.select("LST_Day_1km")
            .multiply(0.02)
            .rename("LST_K")
            .updateMask(mask)
        )
        return lst.copyProperties(img, ["system:time_start"])

    ic = ic_raw.map(apply_qc)

    # -------------------------
    # Weekly loop
    # -------------------------
    n_days = end.difference(start, "day")
    steps = ee.List.sequence(0, n_days.subtract(1), STEP_DAYS).getInfo()

    xs = []   # time (years)
    ys = []   # LST °C

    print(f"\nQC_MODE = {QC_MODE}")
    print(f"Total weekly windows: {len(steps)}\n")

    t0 = None

    for off in steps:
        w_start = start.advance(off, "day")
        w_end   = w_start.advance(STEP_DAYS, "day")
        label   = w_start.format("YYYY-MM-dd").getInfo()

        ic_week = ic.filterDate(w_start, w_end)
        ic_count = ic_week.size().getInfo()

        if ic_count < MIN_IC_COUNT:
            print(f"[{label}] icCount={ic_count} < {MIN_IC_COUNT} -> skip")
            continue

        img = ic_week.mean()

        stat = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=1000,
            bestEffort=True,
            maxPixels=1e13
        )

        val_k = stat.get("LST_K").getInfo()
        if val_k is None:
            print(f"[{label}] ROI mean NULL -> skip")
            continue

        val_c = float(val_k) - 273.15
        print(f"[{label}] icCount={ic_count} | mean={val_c:.2f} °C")

        # prepare for slope
        t = w_start.millis().getInfo() / (1000 * 3600 * 24 * 365.25)
        if t0 is None:
            t0 = t
        xs.append(t - t0)
        ys.append(val_c)

    # -------------------------
    # Trend
    # -------------------------
    if len(xs) >= 10:
        slope, _ = np.polyfit(xs, ys, 1)
        print("\n==============================")
        if slope > 0:
            print(f"📈 Trend: TĂNG  (+{slope:.3f} °C/năm)")
        else:
            print(f"📉 Trend: GIẢM  ({slope:.3f} °C/năm)")
        print("==============================")
    else:
        print("Không đủ dữ liệu để tính trend")

if __name__ == "__main__":
    main()
