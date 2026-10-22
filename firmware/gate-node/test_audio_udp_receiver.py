# Live UDP -> speaker playback test, board B of the two-board direct link.
# Pairs with test_audio_udp_sender.py - run this one FIRST so it's already
# listening (and so you can read the IP it prints, to put into the sender
# board's secrets.py as PEER_IP).
#
# The sender already converts I2S's 32-bit words down to plain 16-bit PCM,
# so this side plays them straight through I2S TX at bits=16 - no format
# conversion needed here, just relaying bytes to the amp.
#
# Wiring: MAX98357A Vin=5V, GND=GND, LRC=GPIO8, BCLK=GPIO7, DIN=GPIO9,
#         GAIN=floating (default ~9dB), SD=3.3V (enable)
#
# Needs secrets.py alongside this file - copy secrets.py.example, fill in
# WIFI_SSID/WIFI_PASSWORD/PEER_IP/PEER_PORT (PEER_IP is unused on this
# side, but the file is shared - PEER_PORT is what this board listens on).

import network
import socket
from machine import Pin, I2S
from time import sleep_ms

from secrets import WIFI_SSID, WIFI_PASSWORD, PEER_PORT

SPK_SCK_PIN = 7
SPK_WS_PIN = 8
SPK_SD_PIN = 9

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
print("-> put this IP into the SENDER board's secrets.py as PEER_IP")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PEER_PORT))
print("Listening on port", PEER_PORT, "...")

speaker = I2S(1, sck=Pin(SPK_SCK_PIN), ws=Pin(SPK_WS_PIN), sd=Pin(SPK_SD_PIN),
              mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE, ibuf=20000)

print("Playing incoming audio - Ctrl+C to stop")
try:
    while True:
        packet, _addr = sock.recvfrom(CHUNK_SAMPLES * 2)
        speaker.write(packet)
except KeyboardInterrupt:
    pass
finally:
    speaker.deinit()
    sock.close()
    print("Stopped.")
