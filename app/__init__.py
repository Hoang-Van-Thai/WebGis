#
# from flask import Flask, render_template
# from app.routes.tvdi_api import tvdi_bp
# from app.routes.lst_api import lst_bp
# from app.routes.ndvi3d_api import ndvi3d_api
# from app.routes.xa_api import xa_bp
#
#
# def create_app():
#     app = Flask(__name__)
#
#     # ====== ROUTE TRANG WEB ======
#     @app.route("/")
#     def index():
#         return render_template("index.html")
#     # ==============================
#
#     # API
#     app.register_blueprint(tvdi_bp, url_prefix="/api/tvdi")
#     app.register_blueprint(lst_bp, url_prefix="/api/lst")
#     app.register_blueprint(ndvi3d_api, url_prefix="/api")
#     app.register_blueprint(xa_bp, url_prefix="/api/xa")
#     from app.services.ndvi_update_3d import update_ndvi
#     try:
#         update_ndvi()
#     except Exception as e:
#         print("Error when updating NDVI:", e)
#     try:
#         from app.services.tvdi_weekly_update import update_tvdi_weekly
#         update_tvdi_weekly()
#         print("TVDI updated.")
#     except Exception as e:
#         print("TVDI update error:", e)
#
#     try:
#         from app.services.lst_weekly_update import update_lst_weekly
#         update_lst_weekly()
#         print("LST updated.")
#     except Exception as e:
#         print("LST update error:", e)
#     return app
# app/__init__.py
from flask import Flask, render_template
from app.routes.tvdi_api import tvdi_bp
from app.routes.lst_api import lst_bp
from app.routes.ndvi3d_api import ndvi3d_api
from app.routes.xa_api import xa_bp


def create_app():
    app = Flask(__name__)

    # Trang web chính
    @app.route("/")
    def index():
        return render_template("index.html")

    # API
    app.register_blueprint(tvdi_bp, url_prefix="/api/tvdi")
    app.register_blueprint(lst_bp, url_prefix="/api/lst")
    app.register_blueprint(ndvi3d_api, url_prefix="/api")
    app.register_blueprint(xa_bp, url_prefix="/api/xa")

    return app
