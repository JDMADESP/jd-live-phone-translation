# # example requires websocket-client library:
# # pip install websocket-client

# import os
# import json
# import websocket

# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# print(OPENAI_API_KEY)

# url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
# headers = [
#     "Authorization: Bearer " + OPENAI_API_KEY,
#     "OpenAI-Beta: realtime=v1"
# ]

# def on_open(ws):
#     print("Connected to server.")

# def on_message(ws, message):
#     data = json.loads(message)
#     print("Received event:", json.dumps(data, indent=2))

# ws = websocket.WebSocketApp(
#     url,
#     header=headers,
#     on_open=on_open,
#     on_message=on_message,
# )

# ws.run_forever()


import os
import json
import websocket
import pyaudio
import base64
import threading # Import threading
import time      # Import time for potential short delays
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_KEY")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000

audio_buffer = b""

def open_audio_port():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    return p, stream

def listening(stream):
    duration = 5 # Record for 5 seconds
    frames = []
    print(f"Recording for {duration} seconds...")
    for i in range(0, int(RATE / CHUNK * duration)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False) # Add exception_on_overflow
            frames.append(data)
        except IOError as e:
            print(f"Error recording audio: {e}")
            break
    audio_data = b''.join(frames)
    return audio_data

def close_audio_port(p, stream): # Added p as argument
    stream.stop_stream()
    stream.close()
    p.terminate() # Terminate PyAudio
    print("Audio closed")

def play_audio(p, audio_data):
    print(f"Playing audio, size: {len(audio_data)} bytes")
    stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        output=True)
    stream.write(audio_data)
    stream.stop_stream()
    stream.close()
    print("Audio playback complete")

# Global WebSocket object and a flag to indicate connection status
global ws_global
ws_global = None
connected = threading.Event() # Event to signal when connected

def on_open(ws):
    global ws_global
    ws_global = ws
    print("Connected to server.")
    connected.set() # Set the event when connected

def on_message(ws, message):
    global audio_buffer
    server_event = json.loads(message)
    # print("Received event:", json.dumps(server_event, indent=2)) # Uncomment for debugging
    if server_event["type"] == "response.audio.delta":
        audio_chunk = base64.b64decode(server_event["delta"])
        print(f"Received audio chunk, size: {len(audio_chunk)} bytes") # Uncomment for debugging
        audio_buffer += audio_chunk
    elif server_event["type"] == "response.audio.done":
        print("Audio response complete, playing buffered audio...")
        # You need to pass 'p' to play_audio if you want to use the same PyAudio instance
        # For simplicity in this example, we'll re-initialize or assume 'p' is accessible.
        # If 'p' is not global or passed around, you might need to re-initialize it here or
        # adjust play_audio to handle its own PyAudio instance.
        _p = pyaudio.PyAudio() # Re-initialize for playing if needed
        play_audio(_p, audio_buffer)
        _p.terminate()
        audio_buffer = b""
    else:
        print(server_event)

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed with status {close_status_code}: {close_msg}")

if __name__ == "__main__":
    print("Opening Audio Ports")
    p, stream = open_audio_port()
    print("Now Listening...")
    output_audio = listening(stream) # returns data of audio
    print("Closing Ports...")
    close_audio_port(p, stream) # Pass p to close_audio_port

    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
    headers = [
        "Authorization: Bearer " + OPENAI_API_KEY,
        "OpenAI-Beta: realtime=v1"
    ]

    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error, # Add error handler
        on_close=on_close  # Add close handler
    )

    # Start the WebSocket in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    # Wait until the WebSocket connection is established
    print("Waiting for WebSocket connection...")
    connected.wait(timeout=10) # Wait for up to 10 seconds

    if not connected.is_set():
        print("Failed to connect to WebSocket server.")
        exit()

    print("WebSocket connected. Sending messages...")

    # Send session update
    session_event = {
        "type": "session.update",
        "session": {
            "instructions": "You are a translator. You will translate any input text into spanish"
        }
    }
    ws.send(json.dumps(session_event))
    print("Sent session.update")

    # Encode audio data before sending
    # The `output_audio` from PyAudio is raw bytes (PCM), which needs to be Base64 encoded.
    encoded_audio = base64.b64encode(output_audio).decode('ascii')

    # Send conversation item with audio
    # conversation_event = {
    #     "type": "conversation.item.create",
    #     "item": {
    #         "type": "message",
    #         "role": "user",
    #         "content": [
    #             {
    #                 "type": "input_audio",
    #                 "audio": encoded_audio, # Send the Base64 encoded audio
    #             }
    #         ],
    #     },
    # }
    conversation_event = {
        "type": "input_audio_buffer.append",
        "audio": encoded_audio
    }
    ws.send(json.dumps(conversation_event))

    commit = {
        "type": "input_audio_buffer.commit"
    }
    ws.send(json.dumps(commit))
    print("Sent conversation.item.create with audio")

    # Keep the main thread alive for a bit to allow responses to come back
    # You might want a more sophisticated way to manage this,
    # e.g., waiting for a specific "done" message from OpenAI or using a shared flag.
    print("Waiting for audio response from OpenAI (main thread will sleep for 15 seconds)...")
    time.sleep(15) # Give it some time to receive audio responses

    print("Process potentially terminated! (Main thread finished its sleep)")
    # You might want to add ws.close() here if you're done with the connection
    # However, for a continuous real-time app, you'd manage connection lifecycle differently.
    ws.close()