import os
import ee


DEFAULT_LOCAL_KEY = "service_account/gee-auto-export.json"
DEFAULT_RENDER_KEY = "/etc/secrets/gee-auto-export.json"

_initialized = False

def init_gee():
    """
    Init Earth Engine 1 lần duy nhất.
    Ưu tiên:
      1) ENV GEE_KEY_PATH (Render)
      2) /etc/secrets/gee-auto-export.json (Render default)
      3) service_account/gee-auto-export.json (local/docker dev)
    """
    global _initialized
    if _initialized:
        return

    service_account = os.getenv(
        "GEE_SERVICE_ACCOUNT",
        "gee-auto-export@vigilant-design-403812.iam.gserviceaccount.com"
    )

    key_path = os.getenv("GEE_KEY_PATH")
    if not key_path:
        key_path = DEFAULT_RENDER_KEY if os.path.exists(DEFAULT_RENDER_KEY) else DEFAULT_LOCAL_KEY

    credentials = ee.ServiceAccountCredentials(service_account, key_path)

    # Nếu bạn cần project thì set ENV GEE_PROJECT, không thì bỏ
    project = os.getenv("GEE_PROJECT")
    if project:
        ee.Initialize(credentials, project=project)
    else:
        ee.Initialize(credentials)

    _initialized = True
