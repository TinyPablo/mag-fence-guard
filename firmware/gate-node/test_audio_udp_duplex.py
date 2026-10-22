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
# Wi-Fi diagnostics run once at startup; audio streaming stays quiet.
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

import binascii
import network
import socket
import uarray as array
from machine import Pin, I2S
from time import sleep_ms, ticks_ms, ticks_diff

from secrets import WIFI_SSID, WIFI_PASSWORD, STATIC_IP, PEER_IP, PEER_PORT, SOURCE

NETMASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS = "192.168.1.1"
CONNECT_TIMEOUT_MS = 20000
BSSIDS = {
    "router": "D4:B7:09:CA:45:36",
    "ap": "08:8A:F1:D9:D4:5E",
}
if SOURCE not in BSSIDS:
    raise ValueError('SOURCE must be "ap" or "router"')
selected_bssid = binascii.unhexlify(BSSIDS[SOURCE].replace(":", ""))

MIC_SCK_PIN = 5
MIC_WS_PIN = 4
MIC_SD_PIN = 6

SPK_SCK_PIN = 7
SPK_WS_PIN = 8
SPK_SD_PIN = 9

RATE = 16000
CHUNK_SAMPLES = 256

def format_bssid(value):
    return ":".join("%02X" % byte for byte in value)


def show_access_points(wlan):
    print("Visible access points for SSID:", WIFI_SSID)
    try:
        matches = [ap for ap in wlan.scan() if ap[0] == WIFI_SSID.encode()]
        for ssid, bssid, channel, rssi, *_ in sorted(
                matches, key=lambda ap: ap[3], reverse=True):
            print("  SSID: %s | BSSID: %s | RSSI: %d dBm | channel: %d" %
                  (ssid.decode(), format_bssid(bssid), rssi, channel))
        if not matches:
            print("  No matching access points found.")
    except (OSError, ValueError) as error:
        print("  Scan unavailable:", error)


def show_connection(wlan):
    print("WiFi connected, IP:", wlan.ifconfig()[0])
    print("  SSID:", wlan.config("essid"))
    print("  Selected source:", SOURCE)
    print("  BSSID (enforced):", BSSIDS[SOURCE])
    print("  Connected RSSI: %d dBm" % wlan.status("rssi"))


wlan = network.WLAN(network.STA_IF)
# Reset the interface so a Thonny rerun cannot retain the previous AP.
wlan.active(False)
wlan.active(True)
show_access_points(wlan)
wlan.ifconfig((STATIC_IP, NETMASK, GATEWAY, DNS))
print("Connecting to WiFi: %s | source: %s | BSSID: %s" %
      (WIFI_SSID, SOURCE, BSSIDS[SOURCE]))
wlan.connect(WIFI_SSID, WIFI_PASSWORD, bssid=selected_bssid)
connect_started = ticks_ms()
while not wlan.isconnected():
    if ticks_diff(ticks_ms(), connect_started) >= CONNECT_TIMEOUT_MS:
        wlan.disconnect()
        raise RuntimeError("WiFi connection timed out for source: " + SOURCE)
    sleep_ms(200)
wlan.config(pm=network.WLAN.PM_NONE)
show_connection(wlan)

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

print("Duplex running - Ctrl+C to stop")
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
except KeyboardInterrupt:
    pass
finally:
    mic.deinit()
    speaker.deinit()
    sock.close()
    print("Stopped.")
