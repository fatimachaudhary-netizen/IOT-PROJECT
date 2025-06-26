import os
import re
import random
import pytz
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from utils.firestore_utils import store_reminder_in_firestore
from firebase.firebase_config import db
from config import UPLOAD_FOLDER, TTS_FOLDER
from utils.audio_handler import save_and_rename_audio
from utils.assembly_ai import transcribe_audio
from utils.intent_parser import interpret_text
from utils.openai_api import generate_chat_response
from utils.google_tts import text_to_speech

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER, exist_ok=True)

app = Flask(__name__)
timezone = pytz.timezone("Asia/Karachi")

def maybe_add_name_to_response(transcript: str, response: str) -> str:
    if "joona" in transcript.lower():
        if random.random() < 0.5:
            return f"Joona here! {response}"
    return response

def is_question(text: str) -> bool:
    question_words = r'\b(how|what|why|when|where|who|are|is|do|does|did|can|could|would|should)\b'
    return bool(re.search(question_words, text.lower()))

def check_reminders():
    now = datetime.now(timezone).strftime('%I%p').lower()
    reminders = db.collection('reminders').stream()
    for doc in reminders:
        data = doc.to_dict()
        time_raw = data.get('time', '')
        reminder_time = str(time_raw).replace(" ", "").lower() if time_raw is not None else ""
        if reminder_time == now:
            print(f"\U0001F514 Reminder: {data.get('response', '')}")

scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', minutes=1)
scheduler.start()

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    content_type = request.content_type or ""

    if "multipart/form-data" in content_type:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        audio = request.files['audio']
        filename = "user_uploaded.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio.save(filepath)
    elif "audio/wav" in content_type:
        filename = "esp32_latest.wav"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        try:
            with open(filepath, "wb") as f:
                f.write(request.get_data())
        except Exception as e:
            print(f"\u274C Error saving audio: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Unsupported Content-Type"}), 400

    print(f"\U0001F3A7 Audio saved: {filename}")

    transcription_result = transcribe_audio(filepath)
    if "text" not in transcription_result:
        return jsonify(transcription_result)

    text = transcription_result["text"]
    interpreted = interpret_text(text)

    if interpreted["intent"] == "unknown" or is_question(text):
        response_text = generate_chat_response(text)
    else:
        response_text = interpreted.get("response", "")

    final_response = maybe_add_name_to_response(text, response_text)
    audio_filename = text_to_speech(final_response)

    if interpreted["intent"] in ["set_reminder_full", "set_reminder_partial", "set_alarm"]:
        reminder_data = {
            "intent": interpreted["intent"],
            "transcript": interpreted["transcript"],
            "task": interpreted.get("task", ""),
            "time": str(interpreted.get("time") or "").replace(" ", "").lower(),
            "response": final_response,
            "category": interpreted.get("category", "task")
        }
        store_reminder_in_firestore(reminder_data)

    response_json = {
        "filename": filename,
        "transcript": text,
        "intent": interpreted["intent"],
        "category": interpreted.get("category", "query"),
        "time": interpreted.get("time"),
        "response": final_response,
        "response_audio": f"/play-audio/{audio_filename}" if audio_filename and audio_filename.endswith(".wav") else None
    }

    print("📩 Final response to ESP32:")
    print(response_json)

    resp = jsonify(response_json)
    resp.headers["Content-Type"] = "application/json"
    return resp

@app.route('/play-audio/<filename>', methods=['GET'])
def play_audio(filename):
    return send_from_directory(TTS_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
