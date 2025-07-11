from flask import Flask
from flask_cors import CORS
from routes.drive_routes import drive_bp  # make sure the path is correct
import os

app = Flask(__name__)
CORS(app)

# Register your blueprint with a URL prefix
app.register_blueprint(drive_bp, url_prefix="/drive")

@app.route("/")
def home():
    return "✅ Framic backend is live and running!"

if __name__ == "__main__":
    # Bind to 0.0.0.0 and use the PORT from environment (Render needs this)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
