
import os
import pandas as pd
import geopandas as gpd
from app.db.mongo import lst_col

# /.../app/services -> /.../app
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # /app/app
DATA_DIR = os.getenv("GIS_DATA_DIR", os.path.join(BASE_DIR, "data"))

WARDS_SHP = os.path.join(DATA_DIR, "wards_hcm.shp")

# ------- cache shapefile để không load lại mỗi request -------
_WARDS = None
_META = None  # (ward_name_col, normalized_key_col)


def _find_col(df, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None


def _load_boundaries():
    global _WARDS, _META
    if _WARDS is not None and _META is not None:
        return

    if not os.path.exists(WARDS_SHP):
        raise FileNotFoundError(f"Không tìm thấy shapefile wards: {WARDS_SHP}")

    wards = gpd.read_file(WARDS_SHP).to_crs(4326)

    # Tên cột chứa tên phường/xã trong shapefile
    ward_name_col = _find_col(wards, ["ten_xa", "xa", "ward", "name_3", "name", "ten"])
    if ward_name_col is None:
        raise ValueError("Không tìm thấy cột tên phường/xã trong shapefile wards_hcm.")

    # Tạo key chuẩn hóa để join ổn định (tránh lỗi khoảng trắng/ký tự)
    wards["_key"] = wards[ward_name_col].astype(str).str.strip()

    _WARDS = wards
    _META = (ward_name_col, "_key")


def build_lst_c_for_date(target_date: str) -> pd.DataFrame:
    """
    Trả về dataframe: [ten_xa, lst_c] cho đúng ngày target_date
    """
    t = pd.to_datetime(target_date).normalize()

    docs = list(lst_col.find({}, {"_id": 0, "ten_xa": 1, "date": 1, "lst_k": 1, "LST_K": 1}))
    if not docs:
        raise RuntimeError("Mongo lst_history không có dữ liệu.")

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"])

    # Chọn cột nhiệt độ Kelvin
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
    out["_key"] = out["ten_xa"].astype(str).str.strip()
    return out


def get_hcm_wards_geojson(date_str: str) -> dict:
    """
    Trả GeoJSON wards_hcm đã join lst_c theo date_str.
    """
    _load_boundaries()
    wards = _WARDS.copy()
    ward_name_col, key_col = _META

    # join lst
    df_temp = build_lst_c_for_date(date_str)

    # ✅ merge bằng key đã strip
    wards = wards.merge(df_temp[[key_col, "lst_c"]], on=key_col, how="left")

    # chỉ giữ vài field cho nhẹ
    wards = wards[[key_col, "lst_c", "geometry"]]

    return wards.__geo_interface__
