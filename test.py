import os
import json
import websocket
from dotenv import load_dotenv
import pyaudio

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key == None:
    raise ValueError("OPENAI_API_KEY not found in .env file")

url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
headers = {
    "Authorization": f"Bearer {api_key}",
    "OpenAI-Beta": "realtime=v1"
}

# Audio configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # OpenAI Realtime API expects 24 kHz audio

# Initialize PyAudio
p = pyaudio.PyAudio()
stream_in = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
stream_out = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

# WebSocket event handlers
def on_open(ws):
    print("Connected to OpenAI Realtime API")
    # Configure session for audio-to-audio translation (e.g., English to Spanish)
    session_config = {
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],
            "instructions": "Translate spoken English to spoken Spanish in real-time.",
            "voice": "alloy",  # Voice for output audio
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"}
        }
    }
    ws.send(json.dumps(session_config))
    print("Session configured for English to Spanish translation")

def on_message(ws, message):
    data = json.loads(message)
    event_type = data.get("type")
    
    if event_type == "response.audio.delta":
        # Decode and play audio output
        audio_chunk = base64.b64decode(data.get("delta"))
        stream_out.write(audio_chunk)
    elif event_type == "response.text.delta":
        # Print translated text (optional for debugging)
        print("Translated text:", data.get("delta"))
    elif event_type == "error":
        print("Error:", data.get("error"))
    else:
        print("Received event:", json.dumps(data, indent=2))

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed:", close_status_code, close_msg)
    # Clean up PyAudio streams
    stream_in.stop_stream()
    stream_in.close()
    stream_out.stop_stream()
    stream_out.close()
    p.terminate()

# Function to capture and send audio
def send_audio(ws):
    print("Starting audio capture. Speak now...")
    while ws.sock and ws.sock.connected:
        try:
            # Read audio chunk from microphone
            audio_data = stream_in.read(CHUNK, exception_on_overflow=False)
            # Encode to base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            # Send audio input event
            audio_event = {
                "type": "input_audio.append",
                "audio": audio_b64
            }
            ws.send(json.dumps(audio_event))
        except Exception as e:
            print("Error sending audio:", e)
            break

# Initialize WebSocket
ws = websocket.WebSocketApp(
    url,
    header=headers,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Start audio sending in a separate thread
audio_thread = threading.Thread(target=send_audio, args=(ws,))
audio_thread.daemon = True

# Run WebSocket in main thread
try:
    ws.run_forever()
    audio_thread.start()
except KeyboardInterrupt:
    print("Closing connection...")
    ws.close()