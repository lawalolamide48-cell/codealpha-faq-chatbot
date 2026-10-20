"""
app.py - Flask server that exposes the FAQ chatbot to the web UI.

Run:  python app.py   then open http://127.0.0.1:5000
"""

from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from chatbot import FAQChatbot

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_FILES = {"style.css", "script.js"}

app = Flask(__name__)
bot = FAQChatbot(BASE_DIR / "faqs.json")


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def public_file(filename):
    if filename not in PUBLIC_FILES:
        abort(404)
    return send_from_directory(BASE_DIR, filename)


@app.get("/api/suggestions")
def suggestions():
    return jsonify({"suggestions": bot.sample_questions()})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", ""))[:500]
    return jsonify(bot.get_response(message))


if __name__ == "__main__":
    app.run(debug=True)
