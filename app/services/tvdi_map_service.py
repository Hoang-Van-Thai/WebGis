# app/services/tvdi_map_service.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon
from app.db.mongo import tvdi_col
import os

# /.../app/services -> /.../app
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.getenv("GIS_DATA_DIR", os.path.join(APP_DIR, "data"))

PROVINCE_SHP = os.path.join(DATA_DIR, "vn_province", "vn_province.shp")
WARDS_SHP    = os.path.join(DATA_DIR, "vn_wards", "vn_wards.shp")

TPHCM_NAMES = {
    "tp. hồ chí minh",
    "thành phố hồ chí minh",
    "ho chi minh",
    "ho chi minh city",
    "hồ chí minh",
}

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


def _normalize_month_str(date_str: str) -> str:
    """
    Nhận 'YYYY-MM' hoặc 'YYYY-MM-DD' -> trả 'YYYY-MM'
    """
    s = str(date_str).strip()
    if len(s) >= 7:
        s = s[:7]
    # validate
    t = pd.to_datetime(s + "-01", errors="coerce")
    if pd.isna(t):
        raise ValueError(f"date không hợp lệ: {date_str}")
    return t.strftime("%Y-%m")


def build_tvdi_for_month(target_date_or_month: str) -> pd.DataFrame:
    """
    Mongo -> pivot month x ten_xa -> interpolate(time)
    -> lấy row tháng target -> return df(ten_xa, tvdi)
    """
    target_month = _normalize_month_str(target_date_or_month)

    docs = list(tvdi_col.find({}, {"_id": 0, "ten_xa": 1, "date": 1, "tvdi": 1}))
    if not docs:
        raise RuntimeError("Mongo tvdi_history không có dữ liệu.")

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["tvdi"] = pd.to_numeric(df["tvdi"], errors="coerce")
    df = df.dropna(subset=["ten_xa", "date"])

    # month_start = đầu tháng
    df["month_start"] = df["date"].dt.to_period("M").dt.to_timestamp(how="start")

    pivot = (
        df[["month_start", "ten_xa", "tvdi"]]
        .drop_duplicates(subset=["month_start", "ten_xa"], keep="last")
        .pivot(index="month_start", columns="ten_xa", values="tvdi")
        .sort_index()
    )

    pivot_interp = pivot.interpolate(method="time", limit_direction="both")

    # tìm index tương ứng với tháng target
    target_ts = pd.to_datetime(target_month + "-01")
    if target_ts not in pivot_interp.index:
        raise RuntimeError(f"Không có tháng {target_month} trong dữ liệu TVDI sau nội suy.")

    row = pivot_interp.loc[target_ts]  # Series ten_xa -> tvdi
    out = row.reset_index()
    out.columns = ["ten_xa", "tvdi"]
    return out


def get_hcm_wards_geojson_tvdi(date_or_month: str) -> dict:
    _load_boundaries()
    provinces = _PROVINCES
    wards = _WARDS
    prov_name_col, ward_name_col, wards_tinh_col, main_poly = _META

    # lọc wards HCM
    if wards_tinh_col:
        wards_hcm = _filter_by_name(wards, wards_tinh_col, TPHCM_NAMES)
    else:
        hcm = _filter_by_name(provinces, prov_name_col, TPHCM_NAMES)
        wards_hcm = gpd.sjoin(wards, hcm[["geometry"]], predicate="within", how="inner").drop(columns=["index_right"])

    # bỏ đảo
    wards_hcm = wards_hcm[wards_hcm.geometry.intersects(main_poly)].copy()

    # join tvdi
    df_tvdi = build_tvdi_for_month(date_or_month)

    wards_hcm["_key"] = wards_hcm[ward_name_col].astype(str).str.strip()
    df_tvdi["_key"] = df_tvdi["ten_xa"].astype(str).str.strip()

    wards_hcm = wards_hcm.merge(df_tvdi[["_key", "tvdi"]], on="_key", how="left")
    wards_hcm = wards_hcm[["_key", "tvdi", "geometry"]]

    return wards_hcm.__geo_interface__
