from firebase_admin import firestore

def store_reminder_in_firestore(data):
    db = firestore.client()
    reminders = db.collection("reminders")

    # Check for existing reminder with same task + time
    existing = reminders.where("task", "==", data["task"]).where("time", "==", data["time"]).stream()
    if any(existing):
        print("⚠️ Reminder already exists. Skipping...")
        return

    reminders.add(data)
    print("✅ Reminder stored in Firestore:", data)
