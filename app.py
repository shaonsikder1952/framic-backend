from flask import Flask
from flask_cors import CORS
from routes.drive_routes import drive_bp  # <-- correct import
from dotenv import load_dotenv
load_dotenv()

import os

app = Flask(__name__)
CORS(app)

# Register blueprint with /drive prefix
app.register_blueprint(drive_bp, url_prefix="/drive")

@app.route("/")
def home():
    return "✅ Framic backend is live and running!"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",  # required for Render
        port=int(os.environ.get("PORT", 10000)),  # Render injects PORT
        debug=True
    )
