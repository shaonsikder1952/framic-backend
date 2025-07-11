from flask import Flask, jsonify
from flask_cors import CORS
from routes.drive_routes import drive_bp

app = Flask(__name__)
CORS(app)  # ✅ This allows cross-origin requests

app.register_blueprint(drive_bp, url_prefix="/api")

@app.route('/')
def home():
    return jsonify({"message": "Framic Backend is running."})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
