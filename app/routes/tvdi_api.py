
from app.services.tvdi_auto_predict import auto_predict_tvdi
from app.services.tvdi_auto_predict import tvdi_history_with_forecast
from flask import Blueprint, request, jsonify, Response
import pandas as pd
from app.db.mongo import tvdi_col
from app.services.tvdi_map_service import get_hcm_wards_geojson_tvdi


tvdi_bp = Blueprint("tvdi", __name__)

@tvdi_bp.route("/auto_predict", methods=["GET"])
def auto_predict():
    xa = request.args.get("xa")
    if not xa:
        return jsonify({"error": "Thiếu tham số xa"}), 400

    result = auto_predict_tvdi(xa)
    return jsonify(result)
@tvdi_bp.route("/chart", methods=["GET"])
def tvdi_chart():
    xa = request.args.get("xa")
    return jsonify(tvdi_history_with_forecast(xa))
@tvdi_bp.get("/geojson")
def tvdi_geojson():
    date = request.args.get("date")
    if not date:
        return Response("Missing ?date=YYYY-MM (or YYYY-MM-DD)", status=400)
    try:
        gj = get_hcm_wards_geojson_tvdi(date)
        return jsonify(gj)
    except Exception as e:
        return Response(str(e), status=500)


@tvdi_bp.get("/available_dates")
def tvdi_available_dates():
    """
    Trả danh sách tháng có trong DB dạng YYYY-MM (sort tăng dần).
    """
    docs = list(tvdi_col.find({}, {"_id": 0, "date": 1}))
    if not docs:
        return jsonify({"dates": []})

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Lấy "YYYY-MM" unique rồi sort
    months = sorted(set(df["date"].dt.to_period("M").astype(str).tolist()))
    return jsonify({"dates": months})
