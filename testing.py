## send a request to 127.0.0.1:5004/receive_audio/david/1 and attach ./output/test.mp3

import requests
import json
import base64
import asyncio
import websockets


def send_david_request():
    url = "http://127.0.0.1:5004/receive_audio/fin/2"
    file_path = "./output/aniismean.mp3"

    with open(file_path, "rb") as f:
        files = {"file": ("test.mp3", f, "audio/mpeg")}
        response = requests.post(url, files=files)

    print("Status code:", response.status_code)
    print("Response:", response.text)


send_david_request()