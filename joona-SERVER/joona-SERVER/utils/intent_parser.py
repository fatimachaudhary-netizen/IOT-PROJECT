import re
from typing import Dict, Optional
import random


class IntentRecognizer:
    def __init__(self):
        self.patterns = {
            # Device control
            "turn_on_device": re.compile(r"(turn on|switch on|activate|turning on)\s+(the\s+)?(?P<device>[\w\s]+)", re.IGNORECASE),
            "turn_off_device": re.compile(r"(turn off|switch off|deactivate|turning off)\s+(the\s+)?(?P<device>[\w\s]+)", re.IGNORECASE),            
            # Weather
            "get_weather": re.compile(r"(what('s| is) the weather|weather (like)? today)", re.IGNORECASE),
            
            # Reminder
            "set_reminder_full": re.compile(r"remind me( to)? (?P<task>.+?) at (?P<time>\d{1,2}(:\d{2})?\s?(am|pm)?)", re.IGNORECASE),
            "set_reminder_partial": re.compile(r"remind me( to)? (?P<task>[\w\s]+)", re.IGNORECASE),

            # Alarm
            "set_alarm": re.compile(r"(set|wake me|wake up) (an )?alarm( for)? (?P<time>\d{1,2}(:\d{2})?\s?(am|pm)?)", re.IGNORECASE),
            
            # Music
            "play_music": re.compile(r"play (some )?(?P<genre>[\w\s]+)?\s?music", re.IGNORECASE),
            
            # Self-awareness
            "joona_intent": re.compile(r"\b(joona|jonah|juna|joonah)\b", re.IGNORECASE),
            
            # Emotions
            "emotion_sad": re.compile(r"\b(i[' ]?m|i am)?\s?(sad|upset|depressed|crying|not okay)\b", re.IGNORECASE),
            "emotion_happy": re.compile(r"\b(i[' ]?m|i am)?\s?(happy|excited|overjoyed|so glad|grateful)\b", re.IGNORECASE),

            # Greetings & Goodbyes
            "greeting": re.compile(r"\b(hi|hello|hey|good morning|good afternoon|salaam)\b", re.IGNORECASE),
            "farewell": re.compile(r"\b(bye|goodbye|see you|good night|take care)\b", re.IGNORECASE),

            # Jokes
            "tell_joke": re.compile(r"(tell me a joke|make me laugh|i want to laugh)", re.IGNORECASE)
        }

        self.jokes = [
            "Why don’t scientists trust atoms? Because they make up everything.",
            "Parallel lines have so much in common. It’s a shame they’ll never meet.",
            "I told my computer I needed a break, and now it won’t stop sending me KitKats.",
        ]

    def extract_time(self, text: str) -> Optional[str]:
        match = re.search(r'\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b', text, flags=re.IGNORECASE)
        return match.group(0) if match else None

    def recognize_intent(self, text: str) -> Dict:
        text_lower = text.lower()

        for intent, pattern in self.patterns.items():
            match = pattern.search(text)
            if match:
                result = {
                    "intent": intent,
                    "transcript": text,
                    "category": self.get_category(intent)
                }

                if intent in ["turn_on_device", "turn_off_device"]:
                    device = match.group("device").strip()
                    result["device"] = device
                    result["response"] = f"{'Turning on' if intent == 'turn_on_device' else 'Turning off'} the {device}."
                    return result

                elif intent == "get_weather":
                    result["response"] = "Checking the skies for you... Hang tight!"
                    return result

                elif intent == "set_reminder_full":
                    task = match.group("task").strip()
                    time_val = match.group("time")
                    result.update({
                        "task": task,
                        "time": time_val,
                        "response": f"Reminder set for: '{task}' at {time_val}."
                    })
                    return result

                elif intent == "set_reminder_partial":
                    task = match.group("task").strip()
                    result.update({
                        "task": task,
                        "time": None,
                        "response": f"Got it! Reminder for '{task}' – but I’ll need a time to schedule it."
                    })
                    return result

                elif intent == "set_alarm":
                    time_val = match.group("time") or self.extract_time(text)
                    result["time"] = time_val
                    result["response"] = f"Alarm is set for {time_val}."
                    return result

                elif intent == "play_music":
                    genre = match.group("genre").strip() if match.group("genre") else "your favorite"
                    result["genre"] = genre
                    result["response"] = f"Playing {genre} music."
                    return result

                elif intent == "joona_intent":
                    result["response"] = "Hey! It’s me Joona. Always ready to vibe or help!"
                    return result

                elif intent.startswith("emotion_"):
                    emotion = intent.split("_")[1]

                    message = {
                        "sad": "I sensed you're feeling down. Want to talk? Or maybe hear a joke?",
                        "happy": "Yesss I love seeing you happy!! Let’s keep this energy going."
                    }[emotion]
                    result["emotion"] = emotion
                    result["response"] = f"I can tell you're {emotion}. {message}"
                    return result

                elif intent == "greeting":
                    result["response"] = random.choice([
                        "Hey hey!",
                        "Hello sunshine!",
                        "Hi there! How can I brighten your day?"
                    ])
                    return result

                elif intent == "farewell":
                    result["response"] = random.choice([
                        "Goodbye for now!",
                        "Take care! I’ll be right here when you need me.",
                        "Bye bye! Sending hugs."
                    ])
                    return result

                elif intent == "tell_joke":
                    result["response"] = random.choice(self.jokes)
                    return result

        # DEFAULT fallback
        return {
            "intent": "unknown",
            "transcript": text,
            "category": "query",
            "response": (
                "Hmm I couldn’t understand that. "
                "Try saying something like 'Turn on the light', 'Remind me to study', or 'Tell me a joke'."
            )
        }

    def get_category(self, intent: str) -> str:
        if intent.startswith("turn_") or intent == "get_weather":
            return "query"
        elif "alarm" in intent or "reminder" in intent:
            return "task"
        elif "emotion" in intent:
            return "emotion"
        elif intent in ["joona_intent", "greeting", "farewell", "tell_joke"]:
            return "interaction"
        else:
            return "query"


intent_recognizer = IntentRecognizer()


def interpret_text(text: str):
    return intent_recognizer.recognize_intent(text)