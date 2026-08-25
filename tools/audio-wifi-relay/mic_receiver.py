#!/usr/bin/env python3
"""TCP server that receives a raw PCM stream from the ESP32 mic test
(firmware/gate-node/test_audio_wifi_mic.py) and saves it as a playable
.wav file. Run this first, then run the ESP32 script. Keeps listening for
a new connection after each recording, so it doesn't need restarting
between test runs - stop it with Ctrl+C when done.

Usage: python3 mic_receiver.py
"""

import socket
import wave
from datetime import datetime
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5005

RATE = 16000
SAMPWIDTH = 4  # bytes - matches bits=32 on the ESP32 side
CHANNELS = 1

OUT_DIR = Path(__file__).parent / "recordings"


def receive_one(srv):
    out_path = OUT_DIR / "mic-{:%Y%m%d-%H%M%S}.wav".format(datetime.now())

    conn, addr = srv.accept()
    print("Connected:", addr)

    data = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
        print("\rReceived {} bytes".format(len(data)), end="", flush=True)
    print()

    conn.close()

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPWIDTH)
        wf.setframerate(RATE)
        wf.writeframes(bytes(data))

    print("Saved {} ({} bytes, ~{:.2f}s)".format(
        out_path, len(data), len(data) / (RATE * SAMPWIDTH)))


def main():
    OUT_DIR.mkdir(exist_ok=True)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print("Listening on {}:{} - waiting for ESP32... (Ctrl+C to stop)".format(HOST, PORT))

    try:
        while True:
            receive_one(srv)
            print("Waiting for next connection...")
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()


if __name__ == "__main__":
    main()
