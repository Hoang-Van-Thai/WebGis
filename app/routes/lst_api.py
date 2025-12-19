# # app/routes/lst_api.py
# from flask import Blueprint, request, jsonify
# from app.services.lst_auto_predict import lst_predict_next_7_weeks
# from app.services.lst_auto_predict import lst_history_with_forecast
#
# lst_bp = Blueprint("lst_bp", __name__)
#
# @lst_bp.route("/auto_predict7", methods=["GET"])
# def auto_predict7():
#     xa = request.args.get("xa")
#     result = lst_predict_next_7_weeks(xa)
#     return jsonify(result)
# @lst_bp.route("/chart", methods=["GET"])
# def lst_chart():
#     xa = request.args.get("xa")
#     return jsonify(lst_history_with_forecast(xa))
from flask import Blueprint, request, jsonify, Response
from app.services.lst_auto_predict import lst_predict_next_7_weeks, lst_history_with_forecast
from app.services.lst_map_service import get_hcm_wards_geojson
from app.db.mongo import lst_col
import pandas as pd
lst_bp = Blueprint("lst_bp", __name__)

@lst_bp.route("/auto_predict7", methods=["GET"])
def auto_predict7():
    xa = request.args.get("xa")
    result = lst_predict_next_7_weeks(xa)
    return jsonify(result)

@lst_bp.route("/chart", methods=["GET"])
def lst_chart():
    xa = request.args.get("xa")
    return jsonify(lst_history_with_forecast(xa))

# ✅ NEW: GeoJSON map endpoint
@lst_bp.get("/geojson")
def lst_geojson():
    date = request.args.get("date")
    if not date:
        return Response("Missing ?date=YYYY-MM-DD", status=400)

    try:
        gj = get_hcm_wards_geojson(date)
        return jsonify(gj)
    except Exception as e:
        return Response(str(e), status=500)
@lst_bp.get("/available_dates")
def lst_available_dates():
    """
    Trả về danh sách ngày có trong DB (yyyy-mm-dd), đã sort tăng dần.
    """
    docs = list(lst_col.find({}, {"_id": 0, "date": 1}))
    if not docs:
        return jsonify({"dates": []})

    df = pd.DataFrame(docs)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # normalize về ngày (00:00) và unique
    dates = sorted({d.normalize() for d in df["date"]})
    out = [d.strftime("%Y-%m-%d") for d in dates]
    return jsonify({"dates": out})