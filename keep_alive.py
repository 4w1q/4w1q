# keep_alive.py
from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "👍 Bot ayakta", 200

def _run():
    port = int(os.environ.get("PORT", 8080))  # Render PORT'u otomatik verir
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=_run, daemon=True).start()
