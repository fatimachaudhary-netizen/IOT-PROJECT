import os
import hashlib
from gtts import gTTS
from pydub import AudioSegment
from config import TTS_FOLDER

def text_to_speech(text: str) -> str:
    """
    Converts text into a WAV file using gTTS and pydub.
    If the audio file for this text already exists, reuses it.
    Returns the filename of the WAV or None on failure.
    """
    # Create a short unique filename using hash of the text
    base_filename = f"tts_{hashlib.md5(text.encode()).hexdigest()[:8]}"
    mp3_filename = base_filename + ".mp3"
    wav_filename = base_filename + ".wav"

    mp3_path = os.path.join(TTS_FOLDER, mp3_filename)
    wav_path = os.path.join(TTS_FOLDER, wav_filename)

    # If WAV already exists, return it
    if os.path.exists(wav_path):
        print(f"[TTS] File already exists: {wav_filename}")
        return wav_filename

    try:
        # Step 1: Generate MP3 using gTTS
        tts = gTTS(text=text, lang="en")
        tts.save(mp3_path)
        print(f"[TTS] MP3 created: {mp3_filename}")

        # Step 2: Convert to 16kHz mono 16-bit WAV using pydub
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(wav_path, format="wav")
        print(f"[TTS] WAV created: {wav_filename}")

        # Clean up: remove MP3
        os.remove(mp3_path)

        return wav_filename

    except Exception as e:
        print(f"[TTS] Error: {e}")
        return None
