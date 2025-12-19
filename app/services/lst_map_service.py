# app/services/lst_map_service.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon
from app.db.mongo import lst_col
import os

# /.../app/services -> /.../app
# APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# DATA_DIR = os.getenv("GIS_DATA_DIR", os.path.join(APP_DIR, "data"))
#
# PROVINCE_SHP = os.path.join(DATA_DIR, "vn_province", "vn_province.shp")
# WARDS_SHP    = os.path.join(DATA_DIR, "vn_wards", "vn_wards.shp")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # /app/app
DATA_DIR = os.path.join(BASE_DIR, "data")

PROVINCE_SHP = os.path.join(DATA_DIR, "vn_province", "vn_province.shp")
WARDS_SHP    = os.path.join(DATA_DIR, "vn_wards", "vn_wards.shp")

TPHCM_NAMES = {
    "tp. hồ chí minh",
    "thành phố hồ chí minh",
    "ho chi minh",
    "ho chi minh city",
    "hồ chí minh",
}

# ------- cache shapefile để không load lại mỗi request -------
_PROVINCES = None
_WARDS = None
_META = None  # (prov_name_col, ward_name_col, wards_tinh_col, main_poly)

def _find_col(df, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None

def _filter_by_name(gdf, col, names_set_lower):
    s = gdf[col].astype(str).str.strip().str.lower()
    return gdf[s.isin(names_set_lower)].copy()

def _load_boundaries():
    global _PROVINCES, _WARDS, _META
    if _PROVINCES is not None and _WARDS is not None and _META is not None:
        return

    provinces = gpd.read_file(PROVINCE_SHP).to_crs(4326)
    wards = gpd.read_file(WARDS_SHP).to_crs(4326)

    prov_name_col = _find_col(provinces, ["ten_tinh","tinh","name_1","adm1_name","province","ten","name"])
    ward_name_col = _find_col(wards, ["ten_xa","xa","ward","name_3","name","ten"])
    wards_tinh_col = _find_col(wards, ["ten_tinh","tinh","name_1","adm1_name","province"])

    if prov_name_col is None or ward_name_col is None:
        raise ValueError("Không tìm thấy cột tên tỉnh/xã trong shapefile.")

    hcm = _filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
    if hcm.empty:
        raise ValueError("Không lọc ra TP.HCM trong layer tỉnh/thành.")

    hcm_geom = hcm.geometry.union_all()
    if isinstance(hcm_geom, MultiPolygon):
        main_poly = max(hcm_geom.geoms, key=lambda g: g.area)
    else:
        main_poly = hcm_geom

    _PROVINCES = provinces
    _WARDS = wards
    _META = (prov_name_col, ward_name_col, wards_tinh_col, main_poly)

def build_lst_c_for_date(target_date: str) -> pd.DataFrame:
    t = pd.to_datetime(target_date).normalize()

    docs = list(lst_col.find({}, {"_id": 0, "ten_xa": 1, "date": 1, "lst_k": 1, "LST_K": 1}))
    if not docs:
        raise RuntimeError("Mongo lst_history không có dữ liệu.")

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])

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

    pivot_interp = pivot.interpolate(method="time", limit_direction="both")

    idx = pivot_interp.index.normalize() == t
    if not idx.any():
        raise RuntimeError(f"Không có ngày {target_date} trong dữ liệu LST sau nội suy.")

    row_k = pivot_interp.loc[idx].iloc[-1]
    row_c = row_k - 273.15

    out = row_c.reset_index()
    out.columns = ["ten_xa", "lst_c"]
    return out

def get_hcm_wards_geojson(date_str: str) -> dict:
    _load_boundaries()
    provinces = _PROVINCES
    wards = _WARDS
    prov_name_col, ward_name_col, wards_tinh_col, main_poly = _META

    # lọc wards HCM
    if wards_tinh_col:
        wards_hcm = _filter_by_name(wards, wards_tinh_col, TPHCM_NAMES)
    else:
        # fallback spatial join nếu shapefile ward không có cột tỉnh
        hcm = _filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
        wards_hcm = gpd.sjoin(wards, hcm[["geometry"]], predicate="within", how="inner").drop(columns=["index_right"])

    # bỏ đảo
    wards_hcm = wards_hcm[wards_hcm.geometry.intersects(main_poly)].copy()

    # join lst
    df_temp = build_lst_c_for_date(date_str)

    wards_hcm["_key"] = wards_hcm[ward_name_col].astype(str).str.strip()
    df_temp["_key"] = df_temp["ten_xa"].astype(str).str.strip()

    wards_hcm = wards_hcm.merge(df_temp[["_key", "lst_c"]], on="_key", how="left")

    # chỉ giữ vài field cho nhẹ
    keep_cols = ["_key", "lst_c", "geometry"]
    wards_hcm = wards_hcm[keep_cols]

    return wards_hcm.__geo_interface__  # dict GeoJSON chuẩn
