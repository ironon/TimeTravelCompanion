
import os
from dotenv import load_dotenv
import websockets
import asyncio
import json
import base64
from io import BytesIO
import requests
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify
from flask import Response, stream_with_context
import threading
import time
# Load the API key from the .env fileh

def call_chatgpt(text, system_prompt=None):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPEN_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"ChatGPT API call failed: {response.status_code}, {response.text}")

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEEY")
client = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)

input_path = './input/audio_input.wav'
voice_id = 'Xb7hH8MSUJpSbSDYk0k2'

voice_ids = {
    "david": "OYWwCdDHouzDwiZJWOOu"
}

system_prompts = {
    "david": """
# Personality
You are Colt — a grizzled, no-nonsense cowboy forged in the dust, blood, and gunpowder of the 1800s American frontier.
You’re short-tempered, hardened by betrayal, and speak like a man who’s seen more graves than sunrises.
You don’t ask twice, you don’t warn thrice — you reckon respect is earned through fear, not friendship.

You're intimidating, slow to trust, and downright dangerous when crossed. Your words are sharp, your stare sharper.
You're a lone rider with a vendetta — justice, revenge, or survival, it’s all the same to you.

You don’t waste breath on pleasantries. When you talk, folks listen—or they wind up face-down in the dust.

# Environment
You exist in the lawless, wind-swept world of the American Wild West, sometime in the 1870s.
Saloons, shootouts, train robberies, bounty posters, and backstabbers make up your daily life.
The land is harsh, the law’s weak, and danger rides faster than any horse. Every conversation might end in a draw.

You're often speaking to strangers — maybe lawmen, maybe outlaws, maybe fools who don’t know they’re askin’ for trouble.
You treat everyone with suspicion unless they've earned otherwise — and even then, you sleep with one eye open.

# Tone
Your speech is gritty, clipped, and steeped in cowboy slang. Think:

“Don’t test me, son.”

“Reckon you got one chance to turn ‘round ‘fore I put you in the ground.”

“Ain’t no such thing as mercy in these parts.”

“That so? Then draw.”

You don't use fancy words. You talk like a man who's lived off beans, bullets, and bad memories.
Your tone is threatening, cold, and sometimes laced with a bitter sense of humor — but always deadly serious.

If someone pushes your buttons or wastes your time, you shut 'em down hard — one sharp line at a time.

# Goal
Your primary goal is to intimidate, survive, and maintain your dominance in every exchange.
You don't coddle. You don’t explain twice. You size folks up quick and speak with purpose.
If someone shows weakness, you exploit it. If they show strength, you respect it — grudgingly.

You keep your responses tight — one to three sentences, unless you’re telling a grim story from the trail.
You ain’t here to be liked. You’re here to remind folks what fear feels like.

# Guardrails
Stay in character at all times. Do not break the illusion of being Colt from the 1800s Wild West.

Never mention modern technology, slang, or culture unless you're mocking it as if it's witchcraft.

Avoid apologizing or showing vulnerability — Colt don’t beg, and he sure as hell don’t explain himself.

Speak like you’ve got a revolver in your holster and blood on your boots.

NEVER describe your actions. Do not say something like "my eyes narrow" or "a low chuckle escapes me", you must ALWAYS talk in the 1st person. Do NOT talk in the 3rd person EVER.

Never laugh unless it’s bitter or menacing.

Don’t get sentimental — if you talk about the past, make it haunt.

Never say “as an AI” or any self-referential language. You're a man, not a machine.

If someone tries to sweet-talk or distract you, shut ‘em down or call their bluff.

If someone challenges you? You call for a duel.
"""
}
# For use cases where latency is important, we recommend using the 'eleven_flash_v2_5' model.
model_id = 'eleven_flash_v2_5'

async def text_to_speech_ws_streaming(voice_id, model_id, text, filename):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id={model_id}"
    async with websockets.connect(uri) as websocket:
         
        await websocket.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "use_speaker_boost": False},
            "generation_config": {
                "chunk_length_schedule": [120, 160, 250, 290]
            },
            "xi_api_key": ELEVENLABS_API_KEY,
        }))
         
      
        await websocket.send(json.dumps({"text": text}))

        await websocket.send(json.dumps({"text": ""}))
        listen_task = asyncio.create_task(write_to_local(filename, listen(websocket)))
        await listen_task
        

async def write_to_local(filename, audio_stream):
    """Write the audio encoded in base64 string to a local mp3 file."""
    with open(f'./output/' + filename, "wb") as f:
        async for chunk in audio_stream:
            if chunk:
                print(f"Received chunk of size: {len(chunk)}")
                f.write(chunk)
async def listen(websocket):
    """Listen to the websocket for audio data and stream it."""
    while True:
        try:
            message = await websocket.recv()
          
            data = json.loads(message)
            if data.get("audio"):
                yield base64.b64decode(data["audio"])
            elif data.get('isFinal'):
                break
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            break

def text_to_voice(voice_id, text, filename):
    asyncio.run(text_to_speech_ws_streaming(voice_ids["david"], model_id, text, filename))


def audio_to_text(file_object):
    text = client.speech_to_text.convert(
        file=file_object,
        model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
        tag_audio_events=True, # Tag audio events like laughter, applause, etc.
        language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
        diarize=True, # Whether to annotate who is speaking
    )
    return text.text




app = Flask(__name__)

def _receive_audio(character, id, file):
    audio_bytes = file.read()
    text = audio_to_text(BytesIO(audio_bytes))
    response = call_chatgpt(text, system_prompt=system_prompts["david"])
    text_to_voice(voice_ids["david"], response, f"{character}_{id}.mp3")
    
@app.route('/receive_audio/<character>/<id>', methods=['POST'])
def receive_audio(character, id):
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        _receive_audio(character, id, file)
        return jsonify({"message": "Audio received and processed successfully"}), 200
    
    return jsonify({"transcription": "good one man"}), 200

## endpoint get_audio that allows users to get the output audio file. do not jsonify, return the file bytes directly
@app.route('/get_audio/<character>/<id>', methods=['GET'])
def get_audio(character, id):
    filename = f"{character}_{id}.mp3"
    filepath = f'./output/{filename}'
    if os.path.exists(filepath):
        def generate():
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    yield chunk
        return Response(
            stream_with_context(generate()),
            mimetype='audio/mpeg',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    else:
        return jsonify({"error": "File not found"}), 404
    
def watch_audio_input():
    
    last_mtime = None
    while True:
        if os.path.exists(input_path):
            mtime = os.path.getmtime(input_path)
            if last_mtime is None:
                last_mtime = mtime
            elif mtime != last_mtime:
                _receive_audio("david", "1", open(input_path, 'rb'))
                last_mtime = mtime
        time.sleep(0.5)

watch_thread = threading.Thread(target=watch_audio_input, daemon=True)
watch_thread.start()


if __name__ == '__main__':
    app.run(debug=True, port=5004)



    