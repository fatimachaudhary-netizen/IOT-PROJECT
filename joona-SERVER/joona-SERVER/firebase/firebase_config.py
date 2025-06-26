import os
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    json_path = os.path.join(os.path.dirname(__file__), 'joona-firebase-adminsdk.json')
    cred = credentials.Certificate(json_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
