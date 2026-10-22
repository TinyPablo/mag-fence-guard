"""Nonblocking Wi-Fi setup and UDP transport for the remote-unlock bench test."""

import binascii
import errno
import network
import socket
from time import ticks_ms, ticks_diff
from secrets import WIFI_SSID, WIFI_PASSWORD, STATIC_IP, PEER_IP, SOURCE

CONTROL_PORT = 5007
BSSIDS = {"router": "D4B709CA4536", "ap": "088AF1D9D45E"}
RETRY_MS = 10000
# Some MicroPython builds expose EAGAIN without its EWOULDBLOCK alias.
WOULD_BLOCK = (errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN))


def format_bssid(value):
    return ":".join("%02X" % b for b in value)


def select_access_points(scan, ssid):
    known = {binascii.unhexlify(value): name for name, value in BSSIDS.items()}
    matches = {}
    for record in scan:
        name, bssid, _channel, rssi = record[:4]
        if name == ssid.encode() and bssid in known:
            if bssid not in matches or rssi > matches[bssid][2]:
                matches[bssid] = (known[bssid], bssid, rssi)
    return sorted(matches.values(), key=lambda entry: entry[2], reverse=True)


class RemoteLink:
    def __init__(self):
        if SOURCE not in ("auto", "router", "ap"):
            raise ValueError('SOURCE must be "auto", "router" or "ap"')
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(False)
        self.wlan.active(True)
        self.wlan.ifconfig((STATIC_IP, "255.255.255.0", "192.168.1.1", "192.168.1.1"))
        self.wlan.config(pm=network.WLAN.PM_NONE)
        self.candidates = []
        self.selected = None
        self.candidate_index = 0
        if SOURCE == "auto":
            print("WiFi scanning for configured router/repeater...")
            try:
                self.candidates = select_access_points(self.wlan.scan(), WIFI_SSID)
            except OSError as error:
                print("WiFi scan failed:", error)
            for name, bssid, rssi in self.candidates:
                print("WiFi candidate:", name, format_bssid(bssid), "RSSI:", rssi, "dBm")
            if not self.candidates:
                print("No known AP visible; retrying configured BSSIDs without scan")
                self.candidates = [(name, binascii.unhexlify(value), None)
                                   for name, value in BSSIDS.items()]
        else:
            self.candidates = [(SOURCE, binascii.unhexlify(BSSIDS[SOURCE]), None)]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", CONTROL_PORT))
        self.sock.setblocking(False)
        self.peer = (PEER_IP, CONTROL_PORT)
        self.connected = False
        self.last_attempt = None
        self.last_error = None

    def poll(self):
        connected = self.wlan.isconnected()
        if connected != self.connected:
            print("WiFi connected" if connected else "WiFi disconnected")
            if connected:
                print("IP:", self.wlan.ifconfig()[0], "mode:", SOURCE,
                      "source:", self.selected[0],
                      "BSSID (enforced):", format_bssid(self.selected[1]),
                      "RSSI:", self.wlan.status("rssi"), "dBm")
            self.connected = connected
        now = ticks_ms()
        if not connected and (self.last_attempt is None or
                              ticks_diff(now, self.last_attempt) >= RETRY_MS):
            self.last_attempt = now
            try:
                self.wlan.disconnect()
                self.selected = self.candidates[self.candidate_index]
                self.candidate_index = (self.candidate_index + 1) % len(self.candidates)
                print("WiFi connecting:", self.selected[0], format_bssid(self.selected[1]))
                self.wlan.connect(WIFI_SSID, WIFI_PASSWORD, bssid=self.selected[1])
            except OSError as error:
                self.error(error)

    def error(self, error):
        code = error.args[0] if error.args else None
        if code != self.last_error:
            print("UDP/WiFi error:", error)
            self.last_error = code

    def receive(self):
        try:
            data, address = self.sock.recvfrom(128)
        except OSError as error:
            if error.args and error.args[0] in WOULD_BLOCK:
                return None
            self.error(error)
            return None
        if address != self.peer:
            return None
        return data

    def send(self, data):
        if not self.wlan.isconnected():
            return False
        try:
            self.sock.sendto(data, self.peer)
            self.last_error = None
            return True
        except OSError as error:
            self.error(error)
            return False

    def close(self):
        self.sock.close()


MODULE_VERSION = "0.4.0"
