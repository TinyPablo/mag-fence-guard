# Full-duplex live audio test - the SAME script runs on both boards, each
# with its own mic + speaker wired up. Builds directly on
# test_audio_udp_sender.py / test_audio_udp_receiver.py (see those files for
# the reasoning behind the 32->16-bit conversion and chunk sizing) - this
# just does both directions in one loop instead of splitting sender/receiver
# across two boards.
#
# Each loop iteration: read one mic chunk, send it to the peer, then drain
# ALL currently-queued incoming packets (not just one) before going back to
# read the mic again - otherwise incoming audio would lag behind by however
# many chunks arrived faster than we drained them.
#
# Prints a level meter bar for the RECEIVED audio only (not the local mic) -
# this is deliberate for diagnosing one-way-only audio: if the bar moves,
# the peer's mic and the network path are both fine and the problem is on
# this board's speaker/wiring; if the bar stays flat, the problem is
# upstream (the peer's mic, or the link to it).
#
# Wiring (both mic AND speaker on every board now):
#   INMP441:  VDD=3.3V, GND=GND, L/R=GND, WS=GPIO4, SCK=GPIO5, SD=GPIO6
#   MAX98357A: Vin=5V, GND=GND, LRC=GPIO8, BCLK=GPIO7, DIN=GPIO9,
#              GAIN=floating, SD=3.3V
#
# Needs secrets.py alongside this file on BOTH boards - copy
# secrets.py.example, fill in WIFI_SSID/WIFI_PASSWORD/STATIC_IP/PEER_IP/
# PEER_PORT. Each board gets its OWN static IP (STATIC_IP) so the peer
# address never drifts after a DHCP renewal - no more re-checking IPs after
# the router reassigns leases. PEER_IP is the OTHER board's STATIC_IP.
# PEER_PORT is the same number on both boards - each listens on it locally
# AND sends to the peer on it.

import network
import socket
import uarray as array
from machine import Pin, I2S
from time import sleep_ms, ticks_ms, ticks_diff

from secrets import WIFI_SSID, WIFI_PASSWORD, STATIC_IP, PEER_IP, PEER_PORT

NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"

MIC_SCK_PIN = 5
MIC_WS_PIN = 4
MIC_SD_PIN = 6

SPK_SCK_PIN = 7
SPK_WS_PIN = 8
SPK_SD_PIN = 9

RATE = 16000
CHUNK_SAMPLES = 256

METER_WIDTH = 40
METER_INTERVAL_MS = 150

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.ifconfig((STATIC_IP, NETMASK, GATEWAY, DNS))
if not wlan.isconnected():
    print("Connecting to WiFi:", WIFI_SSID, "...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        sleep_ms(200)
wlan.config(pm=network.WLAN.PM_NONE)
print("WiFi connected, IP:", wlan.ifconfig()[0])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PEER_PORT))
sock.settimeout(0)
peer_addr = (PEER_IP, PEER_PORT)
print("Duplex with", peer_addr)

mic = I2S(0, sck=Pin(MIC_SCK_PIN), ws=Pin(MIC_WS_PIN), sd=Pin(MIC_SD_PIN),
          mode=I2S.RX, bits=32, format=I2S.MONO, rate=RATE, ibuf=20000)
speaker = I2S(1, sck=Pin(SPK_SCK_PIN), ws=Pin(SPK_WS_PIN), sd=Pin(SPK_SD_PIN),
              mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE, ibuf=20000)

samples32 = array.array('i', [0] * CHUNK_SAMPLES)
samples16 = array.array('h', [0] * CHUNK_SAMPLES)

meter_peak = 0
last_meter_print = ticks_ms()

print("Duplex running - '#' bar below shows RECEIVED audio level - Ctrl+C to stop")
try:
    while True:
        mic.readinto(samples32)
        for i in range(CHUNK_SAMPLES):
            samples16[i] = samples32[i] >> 16
        sock.sendto(samples16, peer_addr)

        while True:
            try:
                packet, _addr = sock.recvfrom(CHUNK_SAMPLES * 2)
            except OSError:
                break
            speaker.write(packet)
            received = array.array('h', packet)
            for s in received:
                if s < 0:
                    s = -s
                if s > meter_peak:
                    meter_peak = s

        now = ticks_ms()
        if ticks_diff(now, last_meter_print) >= METER_INTERVAL_MS:
            bar_len = min(METER_WIDTH, meter_peak * METER_WIDTH // 32768)
            print("#" * bar_len)
            meter_peak = 0
            last_meter_print = now
except KeyboardInterrupt:
    pass
finally:
    mic.deinit()
    speaker.deinit()
    sock.close()
    print("Stopped.")
