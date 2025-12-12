# app/routes/lst_api.py
from flask import Blueprint, request, jsonify
from app.services.lst_auto_predict import lst_predict_next_7_weeks
from app.services.lst_auto_predict import lst_history_with_forecast

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