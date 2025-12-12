# run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True chỉ dùng trong phát triển
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
