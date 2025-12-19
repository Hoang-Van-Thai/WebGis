
from flask import Blueprint, jsonify, request
from app.services.ndvi_auto_predict import predict_ndvi_by_xa
from app.services.ndvi_auto_predict import ndvi_history_with_forecast
from flask import Response
from app.services.ndvi_map_service import get_hcm_wards_geojson_ndvi
from app.db.mongo import ndvi_col
import pandas as pd
ndvi3d_api = Blueprint("ndvi3d_api", __name__)

@ndvi3d_api.route("/ndvi/predict", methods=["GET"])
def ndvi_predict():
    xa = request.args.get("xa")

    if not xa:
        return jsonify({"error": "Thiếu tham số xa"}), 400

    result = predict_ndvi_by_xa(xa)

    # Nếu xảy ra lỗi (không có xã / thiếu data)
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 404

    return jsonify({
        "xa": xa,
        "count": len(result),
        "data": result
    })

@ndvi3d_api.route("/ndvi/chart", methods=["GET"])
def ndvi_chart():
    xa = request.args.get("xa")
    return jsonify(ndvi_history_with_forecast(xa))


@ndvi3d_api.get("/ndvi/geojson")
def ndvi_geojson():
    date = request.args.get("date")
    if not date:
        return Response("Missing ?date=YYYY-MM-DD", status=400)

    try:
        gj = get_hcm_wards_geojson_ndvi(date)
        return jsonify(gj)
    except Exception as e:
        return Response(str(e), status=500)


@ndvi3d_api.get("/ndvi/available_dates")
def ndvi_available_dates():
    dates = ndvi_col.distinct("date")
    if not dates:
        return jsonify({"dates": []})

    out = sorted({pd.to_datetime(d).normalize().strftime("%Y-%m-%d") for d in dates})
    return jsonify({"dates": out})