from flask import Blueprint, request, jsonify
from app.services.tvdi_auto_predict import auto_predict_tvdi
from app.services.tvdi_auto_predict import tvdi_history_with_forecast


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
