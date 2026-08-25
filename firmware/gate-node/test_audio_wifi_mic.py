# Records a fixed-length clip from the INMP441 mic fully into RAM, THEN
# sends it over WiFi to a plain TCP listener running on a Mac
# (tools/audio-wifi-relay/mic_receiver.py), which saves it as a .wav file.
# This board has no storage of its own, so the Mac is the "man in the
# middle" that lets us actually listen to what the mic captured,
# independent of the speaker side.
#
# Recording and sending are two separate phases on purpose - see the
# "record-then-send" note below for why an earlier live-relay version
# produced sped-up/garbled audio.
#
# Wiring (same as test_audio_loopback.py / test_audio_espnow_sender.py):
#   INMP441 VDD=3.3V, GND=GND, L/R=GND, WS=GPIO25, SCK=GPIO26, SD=GPIO33
#
# Needs secrets.py alongside this file on the board - copy
# secrets.py.example, fill in WIFI_SSID/WIFI_PASSWORD/SERVER_IP/SERVER_PORT,
# upload both. Run tools/audio-wifi-relay/mic_receiver.py on the Mac first,
# then run this script.

import gc
import network
import socket
from machine import Pin, I2S
from time import sleep_ms, ticks_ms, ticks_diff

from secrets import WIFI_SSID, WIFI_PASSWORD, SERVER_IP, SERVER_PORT

MIC_SCK_PIN = 26
MIC_WS_PIN = 25
MIC_SD_PIN = 33

RATE = 16000
BITS = 32
BYTES_PER_SAMPLE = 4
DURATION_S = 3  # desired - actual may be shorter, see the free-RAM check below
CHUNK_SAMPLES = 1024
CHUNK_BYTES = CHUNK_SAMPLES * BYTES_PER_SAMPLE

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print("Connecting to WiFi:", WIFI_SSID, "...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        sleep_ms(200)
wlan.config(pm=network.WLAN.PM_NONE)
print("WiFi connected, IP:", wlan.ifconfig()[0])

print("Connecting to", SERVER_IP, ":", SERVER_PORT, "...")
sock = socket.socket()
sock.settimeout(15)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect((SERVER_IP, SERVER_PORT))
print("Connected.")

mic = I2S(0, sck=Pin(MIC_SCK_PIN), ws=Pin(MIC_WS_PIN), sd=Pin(MIC_SD_PIN),
          mode=I2S.RX, bits=BITS, format=I2S.MONO, rate=RATE, ibuf=20000)

# record-then-send: capture the whole clip into a list of small buffers
# first, with NO network calls in this loop - nothing can stall it, so the
# mic is read at the real sample rate throughout. Earlier version wrote to
# the socket inside this loop; occasional 200ms-2s socket.write() stalls
# (WiFi power-save, then Nagle/ACK/buffer delays) meant the I2S DMA buffer
# (ibuf=20000, only ~5 chunks of slack) overflowed and dropped unread
# samples during those stalls. The recording still "completed" with the
# right total byte count, but those bytes were disjoint snapshots spread
# across ~12s of real time instead of one continuous 3s clip - hence the
# sped-up/chipmunk playback. Splitting into many small chunk buffers
# (instead of one ~188KB block) avoids allocating one giant object, but a
# first attempt at DURATION_S=3 (~188KB total) still hit a MemoryError
# partway through - WiFi being active this time (vs. the original loopback
# test, which had no network stack) leaves much less free heap. Check
# what's actually available and cap the duration to fit it, with margin.
gc.collect()
free_bytes = gc.mem_free()
safe_bytes = int(free_bytes * 0.5)  # leave headroom for interpreter/socket/etc
max_chunks = safe_bytes // CHUNK_BYTES
num_chunks = min((RATE * BYTES_PER_SAMPLE * DURATION_S) // CHUNK_BYTES, max_chunks)
actual_duration_s = num_chunks * CHUNK_BYTES / (RATE * BYTES_PER_SAMPLE)
print("Free heap:", free_bytes, "bytes - recording {:.2f}s ({} chunks)".format(
    actual_duration_s, num_chunks))

chunks = []
record_start = ticks_ms()
try:
    for i in range(num_chunks):
        buf = bytearray(CHUNK_BYTES)
        mic.readinto(buf)
        chunks.append(buf)
except MemoryError:
    print("Ran out of RAM at chunk", len(chunks), "- sending what we have")
record_ms = ticks_diff(ticks_ms(), record_start)
mic.deinit()
print("Recorded in", record_ms, "ms ({} chunks, ~{:.2f}s)".format(
    len(chunks), len(chunks) * CHUNK_BYTES / (RATE * BYTES_PER_SAMPLE)))

print("Sending", len(chunks), "chunks over WiFi...")
sent = 0
send_start = ticks_ms()
for buf in chunks:
    sock.write(buf)
    sent += len(buf)
send_ms = ticks_diff(ticks_ms(), send_start)
sock.close()

print("Sent", sent, "bytes in", send_ms, "ms")
print("Done.")
