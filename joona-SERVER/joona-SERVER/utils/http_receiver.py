import os
import requests

# Flask endpoint matching your server's @app.route('/esp32-upload', ...)
SERVER_URL = "http://10.13.44.65:5000/esp32-upload"

# WAV file to test with (must be actual WAV format, not raw PCM)
WAV_FILE_PATH = "test_audio.wav"  # Replace with your actual path

def send_audio_file(filepath):
    if not os.path.exists(filepath):
        print("❌ File not found:", filepath)
        return

    try:
        with open(filepath, "rb") as audio_file:
            headers = {
                "Content-Type": "audio/wav"
            }
            response = requests.post(SERVER_URL, data=audio_file.read(), headers=headers)

        if response.status_code == 200:
            print("✅ Audio file sent successfully")
            print("🧠 Server response:", response.json())
        else:
            print("❌ Failed to send audio file")
            print("🔴 Status Code:", response.status_code)
            print(response.text)

    except Exception as e:
        print("❌ Exception occurred:", e)

if __name__ == "__main__":
    send_audio_file(WAV_FILE_PATH)
