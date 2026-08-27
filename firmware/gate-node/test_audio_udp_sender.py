# Live mic -> UDP streaming test, board A of the two-board direct link
# (no Mac in the middle - see docs/audio.md for why the earlier WiFi+Mac
# relay test doesn't apply here). Reads the INMP441 continuously and sends
# each chunk over UDP as soon as it's captured - this is the real "live"
# case, not the record-then-send workaround used for the Mac relay test.
#
# INMP441 gives 24-bit samples left-justified in a 32-bit I2S word, so the
# top 16 bits of each 32-bit sample are the actual audio - shifting right
# by 16 converts to plain 16-bit PCM before sending, halving the UDP
# payload and keeping each packet under the ~1472-byte no-fragmentation
# limit (256 samples x 2 bytes = 512 bytes per packet).
#
# Wiring: INMP441 VDD=3.3V, GND=GND, L/R=GND, WS=GPIO4, SCK=GPIO5, SD=GPIO6
#
# Needs secrets.py alongside this file - copy secrets.py.example, fill in
# WIFI_SSID/WIFI_PASSWORD/PEER_IP/PEER_PORT (PEER_IP = the receiver
# board's IP), upload both. Run test_audio_udp_receiver.py on the other
# board first so it's listening.

import network
import socket
import uarray as array
from machine import Pin, I2S
from time import sleep_ms

from secrets import WIFI_SSID, WIFI_PASSWORD, PEER_IP, PEER_PORT

MIC_SCK_PIN = 5
MIC_WS_PIN = 4
MIC_SD_PIN = 6

RATE = 16000
CHUNK_SAMPLES = 256

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print("Connecting to WiFi:", WIFI_SSID, "...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        sleep_ms(200)
wlan.config(pm=network.WLAN.PM_NONE)
print("WiFi connected, IP:", wlan.ifconfig()[0])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect((PEER_IP, PEER_PORT))
print("Streaming to", PEER_IP, ":", PEER_PORT)

mic = I2S(0, sck=Pin(MIC_SCK_PIN), ws=Pin(MIC_WS_PIN), sd=Pin(MIC_SD_PIN),
          mode=I2S.RX, bits=32, format=I2S.MONO, rate=RATE, ibuf=20000)

samples32 = array.array('i', [0] * CHUNK_SAMPLES)
samples16 = array.array('h', [0] * CHUNK_SAMPLES)

print("Streaming - Ctrl+C to stop")
try:
    while True:
        mic.readinto(samples32)
        for i in range(CHUNK_SAMPLES):
            samples16[i] = samples32[i] >> 16
        sock.write(samples16)
except KeyboardInterrupt:
    pass
finally:
    mic.deinit()
    sock.close()
    print("Stopped.")
