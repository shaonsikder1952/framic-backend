from flask import Flask
from flask_cors import CORS
from routes.drive_routes import drive_bp  # <-- DO NOT rename this

import os

app = Flask(__name__)
CORS(app)

# Register your blueprint
app.register_blueprint(drive_bp, url_prefix="/drive")

@app.route("/")
def home():
    return "✅ Framic backend is live and running!"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),  # Render will inject PORT
        debug=True
    )
