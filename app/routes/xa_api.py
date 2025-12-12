# app/routes/xa_api.py
from flask import Blueprint, jsonify
from app.db.mongo import xa_col

xa_bp = Blueprint("xa_bp", __name__)

@xa_bp.route("/list", methods=["GET"])
def get_xa_list():
    # Lấy danh sách xã từ Mongo
    xa_list = xa_col.distinct("ten_xa")
    # Nếu muốn sort theo alphabet:
    xa_list = sorted(xa_list)
    return jsonify(xa_list)
