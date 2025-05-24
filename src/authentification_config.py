import collections
import collections.abc
collections.MutableMapping = collections.abc.Mapping


import pyrebase

config = {
    "apiKey": "AIzaSyA5tsEsc1181d7-TW-iVUHQWArc5ctBzT4",
    "authDomain": "ev-charging-app-ec90b.firebaseapp.com",
    "databaseURL": "https://ev-charging-app-ec90b-default-rtdb.europe-west1.firebasedatabase.app",
    "storageBucket": "ev-charging-app-ec90b.firebasestorage.app",
    "projectId": "ev-charging-app-ec90b"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
