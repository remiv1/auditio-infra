from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

API_KEY = os.environ.get("WOL_API_KEY", "change-me")

@app.route("/wol", methods=["POST"])
def wol():
    if request.headers.get("X-API-KEY") != API_KEY:
        return jsonify({"error": "unauthorized"}), 403
    data = request.get_json()
    mac = data.get("mac")
    broadcast = data.get("broadcast", "192.168.1.255")  # Valeur par défaut adaptée au LAN
    if not mac:
        return jsonify({"error": "missing mac"}), 400
    try:
        # Utilisation de l'option -i pour forcer le broadcast sur le LAN physique
        result = subprocess.run(["wakeonlan", "-i", broadcast, mac], capture_output=True, text=True, check=True)
        return jsonify({"result": "sent", "stdout": result.stdout.strip()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
