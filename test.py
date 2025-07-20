import os
import json
import websocket
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000


def open_audio_port():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    return p, stream

def listening(stream):
    duration = 5
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        if i % 10 == 0:  # Log every 10th frame
            print(f"Recorded frame {i}")
    audio_data = b''.join(frames)
    return audio_data

def close_audio_port(stream):
    stream.close()
    stream.stop_stream()
    print("Audio closed")
    return

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

if __name__ == "__main__":
    print("Opening Audio Ports")
    p, stream = open_audio_port()
    print("Now Listening...")
    output_audio = listening(stream) # returns data of audio
    print("Closing Ports...")
    close_audio_port(stream)

    print("Playing audio back...")
    play_audio(p, output_audio)

    print("Process terminated!")