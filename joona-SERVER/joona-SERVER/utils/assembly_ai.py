import time
import requests
from config import ASSEMBLY_BASE_URL, HEADERS

def transcribe_audio(filepath):
    print(f"Uploading audio file: {filepath}")
    with open(filepath, "rb") as f:
        upload_response = requests.post(
            f"{ASSEMBLY_BASE_URL}/v2/upload",
            headers={"authorization": HEADERS["authorization"]},
            data=f
        )

    if upload_response.status_code != 200:
        return {"error": "Upload failed", "details": upload_response.text}

    audio_url = upload_response.json().get("upload_url")
    if not audio_url:
        return {"error": "Failed to get audio URL"}

    transcript_response = requests.post(
        f"{ASSEMBLY_BASE_URL}/v2/transcript",
        json={"audio_url": audio_url},
        headers=HEADERS
    )

    transcript_id = transcript_response.json().get('id')
    polling_endpoint = f"{ASSEMBLY_BASE_URL}/v2/transcript/{transcript_id}"

    while True:
        result = requests.get(polling_endpoint, headers=HEADERS).json()
        if result['status'] == 'completed':
            return {"text": result['text']}
        elif result['status'] == 'error':
            return {"error": "Transcription failed", "details": result.get('error')}
        time.sleep(2)
