from flask import Flask
from flask_cors import CORS
from routes.drive_routes import drive_bp  # <-- your real routes

app = Flask(__name__)
CORS(app)

app.register_blueprint(drive_bp, url_prefix="/drive")  # <-- connect it properly

@app.route("/")
def home():
    return "Framic backend is running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)  # <-- bind to all IPs
