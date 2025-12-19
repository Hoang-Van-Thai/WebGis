# # test_lst_all_xa_one_day_print_celsius.py
# import pandas as pd
# from app.db.mongo import lst_col
#
# TARGET_DATE = "2025-12-14"  # yyyy-mm-dd
#
# def main():
#     t = pd.to_datetime(TARGET_DATE).normalize()
#
#     docs = list(
#         lst_col.find(
#             {},
#             {"_id": 0, "ten_xa": 1, "date": 1, "lst_k": 1, "LST_K": 1}
#         )
#     )
#     if not docs:
#         print("⚠ Mongo không có dữ liệu.")
#         return
#
#     df = pd.DataFrame(docs)
#     df["date"] = pd.to_datetime(df["date"])
#
#     # chuẩn cột giá trị về LST_K (Kelvin)
#     val_col = "LST_K" if ("LST_K" in df.columns and df["LST_K"].notna().any()) else "lst_k"
#     df.rename(columns={val_col: "LST_K"}, inplace=True)
#     df["LST_K"] = pd.to_numeric(df["LST_K"], errors="coerce")
#
#     pivot = (
#         df[["date", "ten_xa", "LST_K"]]
#         .dropna(subset=["ten_xa"])
#         .drop_duplicates(subset=["date", "ten_xa"], keep="last")
#         .pivot(index="date", columns="ten_xa", values="LST_K")
#         .sort_index()
#     )
#
#     pivot_interp = pivot.interpolate(method="time", limit_direction="both")
#
#     idx = pivot_interp.index.normalize() == t
#     if not idx.any():
#         print(f"⚠ Không có ngày {TARGET_DATE} trong dữ liệu sau nội suy.")
#         print("Gợi ý 5 ngày gần nhất:", pivot_interp.index.sort_values().tail(5).tolist())
#         return
#
#     row_k = pivot_interp.loc[idx].iloc[-1]                  # Kelvin
#     row_c = row_k - 273.15                                  # Celsius
#
#     print(f"\n=== LST (INTERPOLATED) FOR ALL XA ON {TARGET_DATE} ===")
#     print(f"Total xa: {len(row_k)}")
#     print("(format: Kelvin -> Celsius)")
#
#     for ten_xa in row_k.index:
#         k = row_k[ten_xa]
#         c = row_c[ten_xa]
#         if pd.isna(k):
#             print(f"{ten_xa}: NULL")
#         else:
#             print(f"{ten_xa}: {k:.3f} K -> {c:.3f} °C")
#
# if __name__ == "__main__":
#     main()
# import geopandas as gpd
# import folium
#
# # ====== ĐƯỜNG DẪN SHP (SỬA THEO MÁY BẠN) ======
# PROVINCE_SHP = r"D:\API\vn_province\vn_province.shp"
# WARDS_SHP    = r"D:\API\vn_wards\vn_wards.shp"
#
# TPHCM_NAMES = [
#     "TP. Hồ Chí Minh",
#     "Thành phố Hồ Chí Minh",
#     "Ho Chi Minh",
#     "Ho Chi Minh City",
#     "Hồ Chí Minh",
# ]
#
# def find_col(df, candidates):
#     cols = {c.lower(): c for c in df.columns}
#     for cand in candidates:
#         if cand.lower() in cols:
#             return cols[cand.lower()]
#     return None
#
# def pick_name_col(gdf):
#     # đoán cột tên tỉnh/thành phổ biến
#     return find_col(gdf, ["ten_tinh", "tinh", "name_1", "adm1_name", "province", "ten", "name"])
#
# def pick_ward_col(gdf):
#     # đoán cột tên xã/phường phổ biến
#     return find_col(gdf, ["ten_xa", "xa", "ward", "name_3", "name", "ten"])
#
# def filter_by_name(gdf, col, names):
#     if col is None:
#         raise ValueError(f"Không tìm thấy cột tên trong file. Columns = {list(gdf.columns)}")
#     s = gdf[col].astype(str)
#     mask = False
#     for n in names:
#         mask = mask | (s.str.strip().str.lower() == n.strip().lower())
#     return gdf[mask].copy()
#
# def main():
#     # 1) Load shapefiles
#     provinces = gpd.read_file(PROVINCE_SHP)
#     wards = gpd.read_file(WARDS_SHP)
#
#     # 2) Chuẩn CRS về WGS84 để folium hiển thị
#     if provinces.crs is None:
#         print("⚠ provinces CRS is None, bạn cần gán CRS đúng trước khi to_crs.")
#     if wards.crs is None:
#         print("⚠ wards CRS is None, bạn cần gán CRS đúng trước khi to_crs.")
#
#     provinces = provinces.to_crs(4326)
#     wards = wards.to_crs(4326)
#
#     # 3) Lọc TP.HCM từ layer tỉnh/thành
#     prov_name_col = pick_name_col(provinces)
#     hcm = filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
#
#     if hcm.empty:
#         raise ValueError(
#             f"Không lọc ra TP.HCM trong layer tỉnh/thành. "
#             f"Bạn kiểm tra cột tên '{prov_name_col}' và giá trị thực tế."
#         )
#
#     # 4) Lọc các phường/xã thuộc TP.HCM:
#     #    - Ưu tiên nếu có cột ten_tinh trong wards -> lọc theo ten_tinh
#     wards_tinh_col = find_col(wards, ["ten_tinh", "tinh", "name_1", "adm1_name", "province"])
#     if wards_tinh_col:
#         wards_hcm = filter_by_name(wards, wards_tinh_col, TPHCM_NAMES)
#     else:
#         # Không có cột tỉnh -> dùng spatial join: wards nằm trong polygon TP.HCM
#         wards_hcm = gpd.sjoin(wards, hcm[["geometry"]], predicate="within", how="inner").drop(columns=["index_right"])
#
#     if wards_hcm.empty:
#         raise ValueError("Không lọc ra phường/xã TP.HCM. Thử kiểm tra CRS hoặc thuộc tính tên tỉnh trong wards.")
#
#     # 5) Tạo map
#     center = hcm.geometry.unary_union.centroid
#     m = folium.Map(location=[center.y, center.x], zoom_start=10, tiles="OpenStreetMap")
#
#     # Vẽ TP.HCM (tỉnh/thành)
#     folium.GeoJson(
#         hcm,
#         name="TP.HCM boundary",
#         style_function=lambda x: {"fillOpacity": 0.05, "weight": 3},
#         tooltip=folium.GeoJsonTooltip(fields=[prov_name_col], aliases=["Tỉnh/Thành:"])
#     ).add_to(m)
#
#     # Vẽ phường/xã TP.HCM
#     ward_name_col = pick_ward_col(wards_hcm)
#     tooltip_fields = []
#     tooltip_aliases = []
#     if ward_name_col:
#         tooltip_fields.append(ward_name_col)
#         tooltip_aliases.append("Xã/Phường:")
#     if wards_tinh_col:
#         tooltip_fields.append(wards_tinh_col)
#         tooltip_aliases.append("Thuộc:")
#
#     folium.GeoJson(
#         wards_hcm,
#         name="Wards/Communes (TP.HCM)",
#         style_function=lambda x: {"fillOpacity": 0.15, "weight": 1},
#         tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases) if tooltip_fields else None
#     ).add_to(m)
#
#     folium.LayerControl().add_to(m)
#
#     out_html = "tphcm_wards_map.html"
#     m.save(out_html)
#     print("✅ Saved:", out_html)
#     print("TP.HCM provinces rows:", len(hcm))
#     print("TP.HCM wards rows    :", len(wards_hcm))
#     print("Province name col    :", prov_name_col)
#     print("Ward name col        :", ward_name_col)
#     print("Wards tinh col       :", wards_tinh_col)
#
# if __name__ == "__main__":
#     main()
# import pandas as pd
# import geopandas as gpd
# import matplotlib.pyplot as plt
#
# from app.db.mongo import lst_col
#
# # =========================
# # CONFIG
# # =========================
# TARGET_DATE = "2025-12-14"   # yyyy-mm-dd
# OUT_PNG = f"tphcm_lst_{TARGET_DATE}.png"
#
# PROVINCE_SHP = r"D:\API\vn_province\vn_province.shp"
# WARDS_SHP    = r"D:\API\vn_wards\vn_wards.shp"
#
# TPHCM_NAMES = {
#     "tp. hồ chí minh",
#     "thành phố hồ chí minh",
#     "ho chi minh",
#     "ho chi minh city",
#     "hồ chí minh",
# }
#
# # =========================
# # HELPERS
# # =========================
# def find_col(df, candidates):
#     cols = {c.lower(): c for c in df.columns}
#     for cand in candidates:
#         if cand.lower() in cols:
#             return cols[cand.lower()]
#     return None
#
# def filter_by_name(gdf, col, names_set_lower):
#     s = gdf[col].astype(str).str.strip().str.lower()
#     return gdf[s.isin(names_set_lower)].copy()
#
# def build_lst_c_for_date(target_date: str) -> pd.DataFrame:
#     """
#     Load ALL LST from Mongo -> pivot date x ten_xa -> interpolate(time)
#     -> get 1 row (target_date) -> convert K to C -> return df_temp(ten_xa, lst_c)
#     """
#     t = pd.to_datetime(target_date).normalize()
#
#     docs = list(
#         lst_col.find(
#             {},
#             {"_id": 0, "ten_xa": 1, "date": 1, "lst_k": 1, "LST_K": 1}
#         )
#     )
#     if not docs:
#         raise RuntimeError("Mongo lst_history không có dữ liệu.")
#
#     df = pd.DataFrame(docs)
#     df["date"] = pd.to_datetime(df["date"])
#
#     # chuẩn cột giá trị về LST_K (Kelvin)
#     val_col = "LST_K" if ("LST_K" in df.columns and df["LST_K"].notna().any()) else "lst_k"
#     df.rename(columns={val_col: "LST_K"}, inplace=True)
#     df["LST_K"] = pd.to_numeric(df["LST_K"], errors="coerce")
#
#     pivot = (
#         df[["date", "ten_xa", "LST_K"]]
#         .dropna(subset=["ten_xa"])
#         .drop_duplicates(subset=["date", "ten_xa"], keep="last")
#         .pivot(index="date", columns="ten_xa", values="LST_K")
#         .sort_index()
#     )
#
#     pivot_interp = pivot.interpolate(method="time", limit_direction="both")
#
#     idx = pivot_interp.index.normalize() == t
#     if not idx.any():
#         raise RuntimeError(f"Không có ngày {target_date} trong dữ liệu LST sau nội suy.")
#
#     row_k = pivot_interp.loc[idx].iloc[-1]          # Kelvin
#     row_c = row_k - 273.15                          # Celsius
#
#     df_temp = row_c.reset_index()
#     df_temp.columns = ["ten_xa", "lst_c"]
#
#     return df_temp
#
#
# def main():
#     # 1) Load shapefiles
#     provinces = gpd.read_file(PROVINCE_SHP).to_crs(4326)
#     wards     = gpd.read_file(WARDS_SHP).to_crs(4326)
#
#     prov_name_col = find_col(provinces, ["ten_tinh", "tinh", "name_1", "adm1_name", "province", "ten", "name"])
#     ward_name_col = find_col(wards, ["ten_xa", "xa", "ward", "name_3", "name", "ten"])
#     wards_tinh_col = find_col(wards, ["ten_tinh", "tinh", "name_1", "adm1_name", "province"])
#
#     if prov_name_col is None:
#         raise ValueError(f"Không tìm thấy cột tên tỉnh trong provinces. Columns={list(provinces.columns)}")
#     if ward_name_col is None:
#         raise ValueError(f"Không tìm thấy cột tên xã trong wards. Columns={list(wards.columns)}")
#
#     # 2) Lọc TP.HCM
#     hcm = filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
#     if hcm.empty:
#         raise ValueError("Không lọc ra TP.HCM trong layer tỉnh/thành.")
#
#     if wards_tinh_col:
#         wards_hcm = filter_by_name(wards, wards_tinh_col, TPHCM_NAMES)
#     else:
#         # fallback: spatial within
#         wards_hcm = gpd.sjoin(wards, hcm[["geometry"]], predicate="within", how="inner").drop(columns=["index_right"])
#
#     if wards_hcm.empty:
#         raise ValueError("Không lọc ra phường/xã TP.HCM. Kiểm tra CRS/thuộc tính.")
#
#     # 3) Lấy nhiệt độ (°C) từ Mongo (đã nội suy) cho 1 ngày
#     df_temp = build_lst_c_for_date(TARGET_DATE)
#
#     # 4) Join theo ten_xa
#     # (đảm bảo cùng format chữ)
#     wards_hcm = wards_hcm.copy()
#     wards_hcm["_key"] = wards_hcm[ward_name_col].astype(str).str.strip()
#     df_temp["_key"] = df_temp["ten_xa"].astype(str).str.strip()
#
#     wards_hcm = wards_hcm.merge(df_temp[["_key", "lst_c"]], on="_key", how="left")
#
#     # 5) Plot + export PNG
#     fig, ax = plt.subplots(figsize=(10, 10), dpi=200)
#
#     # nền: boundary TP.HCM
#     hcm.boundary.plot(ax=ax, linewidth=2)
#
#     # wards colored by lst_c
#     # missing values: gray
#     wards_hcm.plot(
#         ax=ax,
#         column="lst_c",
#         legend=True,
#         cmap="viridis",
#         missing_kwds={"color": "lightgray", "label": "No data"},
#         linewidth=0.2,
#         edgecolor="white",
#     )
#
#     ax.set_title(f"TP.HCM LST (°C) — {TARGET_DATE}", fontsize=14)
#     ax.set_axis_off()
#
#     plt.tight_layout()
#     plt.savefig(OUT_PNG, bbox_inches="tight")
#     plt.close(fig)
#
#     # 6) Log
#     total = len(wards_hcm)
#     missing = wards_hcm["lst_c"].isna().sum()
#     print("✅ Saved PNG:", OUT_PNG)
#     print("TP.HCM wards:", total, "| missing lst_c:", missing)
#     if total - missing > 0:
#         print("LST °C min/mean/max:",
#               float(wards_hcm["lst_c"].min()),
#               float(wards_hcm["lst_c"].mean()),
#               float(wards_hcm["lst_c"].max()))
#
# if __name__ == "__main__":
#     main()
# export_tphcm_lst_palette_png.py
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
from shapely.geometry import MultiPolygon

from app.db.mongo import lst_col

# =========================
# CONFIG
# =========================
TARGET_DATE = "2025-12-14"  # yyyy-mm-dd
OUT_PNG = f"tphcm_lst_{TARGET_DATE}_palette.png"

PROVINCE_SHP = r"D:\API\vn_province\vn_province.shp"
WARDS_SHP = r"D:\API\vn_wards\vn_wards.shp"

TPHCM_NAMES = {
    "tp. hồ chí minh",
    "thành phố hồ chí minh",
    "ho chi minh",
    "ho chi minh city",
    "hồ chí minh",
}

# Palette bạn yêu cầu (lạnh -> nóng)
LST_PALETTE = [
    "#0000FF", "#0066FF", "#00FFFF", "#00FF00",
    "#FFFF00", "#FFCC00", "#FF6600", "#FF0000"
]

# Range giống GEE UI (bạn có thể đổi)
V_MIN = 10.0
V_MAX = 45.0


# =========================
# HELPERS
# =========================
def find_col(df, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None


def filter_by_name(gdf, col, names_set_lower):
    s = gdf[col].astype(str).str.strip().str.lower()
    return gdf[s.isin(names_set_lower)].copy()


def build_lst_c_for_date(target_date: str) -> pd.DataFrame:
    """
    Load ALL LST from Mongo -> pivot date x ten_xa -> interpolate(time)
    -> get 1 row (target_date) -> convert Kelvin to Celsius -> return df_temp(ten_xa, lst_c)
    """
    t = pd.to_datetime(target_date).normalize()

    docs = list(
        lst_col.find(
            {},
            {"_id": 0, "ten_xa": 1, "date": 1, "lst_k": 1, "LST_K": 1}
        )
    )
    if not docs:
        raise RuntimeError("Mongo lst_history không có dữ liệu.")

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])

    # chuẩn cột giá trị về LST_K (Kelvin)
    val_col = "LST_K" if ("LST_K" in df.columns and df["LST_K"].notna().any()) else "lst_k"
    df.rename(columns={val_col: "LST_K"}, inplace=True)
    df["LST_K"] = pd.to_numeric(df["LST_K"], errors="coerce")

    pivot = (
        df[["date", "ten_xa", "LST_K"]]
        .dropna(subset=["ten_xa"])
        .drop_duplicates(subset=["date", "ten_xa"], keep="last")
        .pivot(index="date", columns="ten_xa", values="LST_K")
        .sort_index()
    )

    # nội suy theo thời gian (theo từng xã)
    pivot_interp = pivot.interpolate(method="time", limit_direction="both")

    idx = pivot_interp.index.normalize() == t
    if not idx.any():
        raise RuntimeError(f"Không có ngày {target_date} trong dữ liệu LST sau nội suy.")

    row_k = pivot_interp.loc[idx].iloc[-1]   # Kelvin
    row_c = row_k - 273.15                   # Celsius

    df_temp = row_c.reset_index()
    df_temp.columns = ["ten_xa", "lst_c"]
    return df_temp


def main():
    # 1) Load shapefiles
    provinces = gpd.read_file(PROVINCE_SHP)
    wards = gpd.read_file(WARDS_SHP)

    # 2) To WGS84 for plotting
    provinces = provinces.to_crs(4326)
    wards = wards.to_crs(4326)

    # 3) Find columns
    prov_name_col = find_col(provinces, ["ten_tinh", "tinh", "name_1", "adm1_name", "province", "ten", "name"])
    ward_name_col = find_col(wards, ["ten_xa", "xa", "ward", "name_3", "name", "ten"])
    wards_tinh_col = find_col(wards, ["ten_tinh", "tinh", "name_1", "adm1_name", "province"])

    if prov_name_col is None:
        raise ValueError(f"Không tìm thấy cột tên tỉnh trong provinces. Columns={list(provinces.columns)}")
    if ward_name_col is None:
        raise ValueError(f"Không tìm thấy cột tên xã trong wards. Columns={list(wards.columns)}")

    # 4) Filter HCMC province polygon
    hcm = filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
    if hcm.empty:
        raise ValueError("Không lọc ra TP.HCM trong layer tỉnh/thành (kiểm tra ten_tinh).")

    # 5) Filter wards in HCMC
    if wards_tinh_col:
        wards_hcm = filter_by_name(wards, wards_tinh_col, TPHCM_NAMES)
    else:
        wards_hcm = gpd.sjoin(wards, hcm[["geometry"]], predicate="within", how="inner").drop(columns=["index_right"])

    if wards_hcm.empty:
        raise ValueError("Không lọc ra phường/xã TP.HCM. Kiểm tra CRS/thuộc tính.")

    # ===== KEEP ONLY MAINLAND (REMOVE ISLAND CLUSTER) =====
    # lấy geometry TP.HCM và chọn polygon lớn nhất
    hcm_geom = hcm.geometry.union_all()
    if isinstance(hcm_geom, MultiPolygon):
        main_poly = max(hcm_geom.geoms, key=lambda g: g.area)
    else:
        main_poly = hcm_geom

    before = len(wards_hcm)
    wards_hcm = wards_hcm[wards_hcm.geometry.intersects(main_poly)].copy()
    after = len(wards_hcm)
    print(f"🧹 Removed non-mainland polygons: {before - after} | kept: {after}")

    # 6) Load LST (°C) from Mongo for target date (interpolated)
    df_temp = build_lst_c_for_date(TARGET_DATE)

    # 7) Join by ten_xa
    wards_hcm = wards_hcm.copy()
    wards_hcm["_key"] = wards_hcm[ward_name_col].astype(str).str.strip()
    df_temp["_key"] = df_temp["ten_xa"].astype(str).str.strip()

    wards_hcm = wards_hcm.merge(df_temp[["_key", "lst_c"]], on="_key", how="left")

    # 8) Plot to PNG with palette
    cmap = ListedColormap(LST_PALETTE)
    norm = Normalize(vmin=V_MIN, vmax=V_MAX)

    fig, ax = plt.subplots(figsize=(10, 10), dpi=220)

    # Boundary TP.HCM (cũng chỉ vẽ mainland cho đồng bộ)
    gpd.GeoSeries([main_poly], crs=provinces.crs).boundary.plot(ax=ax, linewidth=2, color="black")

    wards_hcm.plot(
        ax=ax,
        column="lst_c",
        cmap=cmap,
        norm=norm,
        linewidth=0.25,
        edgecolor="white",
        missing_kwds={"color": "lightgray", "label": "No data"},
    )

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)
    cbar.set_label("LST (°C)")

    ax.set_title(f"TP.HCM LST (°C) — {TARGET_DATE}", fontsize=14)
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUT_PNG, bbox_inches="tight")
    plt.close(fig)

    total = len(wards_hcm)
    missing = int(wards_hcm["lst_c"].isna().sum())
    print("✅ Saved PNG:", OUT_PNG)
    print("TP.HCM wards:", total, "| missing lst_c:", missing)

    if total - missing > 0:
        print(
            "LST °C min/mean/max:",
            float(wards_hcm["lst_c"].min()),
            float(wards_hcm["lst_c"].mean()),
            float(wards_hcm["lst_c"].max()),
        )


if __name__ == "__main__":
    main()

