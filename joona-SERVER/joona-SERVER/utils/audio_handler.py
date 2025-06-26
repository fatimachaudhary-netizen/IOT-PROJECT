import os
from config import UPLOAD_FOLDER

def save_and_rename_audio(audio_file, filename):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)
    print(f"Audio saved as: {filepath}")
    return filepath
