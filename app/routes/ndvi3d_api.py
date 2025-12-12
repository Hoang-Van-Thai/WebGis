
from flask import Blueprint, jsonify, request
from app.services.ndvi_auto_predict import predict_ndvi_by_xa
from app.services.ndvi_auto_predict import ndvi_history_with_forecast
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