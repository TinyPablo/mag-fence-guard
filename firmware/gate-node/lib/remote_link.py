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


class RemoteLink:
    def __init__(self):
        if SOURCE not in BSSIDS:
            raise ValueError('SOURCE must be "router" or "ap"')
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(False)
        self.wlan.active(True)
        self.wlan.ifconfig((STATIC_IP, "255.255.255.0", "192.168.1.1", "192.168.1.1"))
        self.wlan.config(pm=network.WLAN.PM_NONE)
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
                print("IP:", self.wlan.ifconfig()[0], "source:", SOURCE,
                      "BSSID (enforced):", BSSIDS[SOURCE],
                      "RSSI:", self.wlan.status("rssi"), "dBm")
            self.connected = connected
        now = ticks_ms()
        if not connected and (self.last_attempt is None or
                              ticks_diff(now, self.last_attempt) >= RETRY_MS):
            self.last_attempt = now
            try:
                self.wlan.disconnect()
                self.wlan.connect(WIFI_SSID, WIFI_PASSWORD,
                                  bssid=binascii.unhexlify(BSSIDS[SOURCE]))
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
            if error.args and error.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
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
