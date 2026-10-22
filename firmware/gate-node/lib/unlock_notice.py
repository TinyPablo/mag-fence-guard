"""Short-lived unlock events bound to a recently advertised house token."""

import os
from time import ticks_ms, ticks_diff
from lib.intercom_session import valid_id


class UnlockNotice:
    def __init__(self, link, role):
        self.link = link
        self.role = role
        self.last_ready = None
        self.tokens = []
        self.remote_token = None
        self.remote_at = 0
        self.pending = None
        self.started = 0
        self.last_send = None
        self.seen = []

    def notify(self, source):
        now = ticks_ms()
        if (not self.link.wlan.isconnected() or self.remote_token is None or
                ticks_diff(now, self.remote_at) >= 1000):
            print("Unlock notice skipped: house not recently available")
            return
        event_id = os.urandom(12).hex().encode()
        packet = b"OPENED " + self.remote_token + b" " + event_id + b" " + source.encode()
        self.pending = (event_id, packet)
        self.started = now
        self.last_send = None

    def receive(self, packet):
        parts = packet.split()
        now = ticks_ms()
        if self.role == "gate":
            if len(parts) == 2 and parts[0] == b"READY" and valid_id(parts[1]):
                self.remote_token = parts[1]
                self.remote_at = now
            elif (len(parts) == 2 and parts[0] == b"EVENT_ACK" and
                  self.pending is not None and parts[1] == self.pending[0]):
                self.pending = None
            return None
        if len(parts) != 4 or parts[0] != b"OPENED" or not valid_id(parts[2]):
            return None
        if not any(token == parts[1] and ticks_diff(now, at) < 1000 for token, at in self.tokens):
            return None
        if parts[3] not in (b"house", b"pir") and not parts[3].startswith(b"rfid:"):
            return None
        self.link.send(b"EVENT_ACK " + parts[2])
        if parts[2] in self.seen:
            return None
        self.seen.append(parts[2])
        self.seen = self.seen[-32:]
        print("Gate unlocked; source:", parts[3].decode())
        return parts[3]

    def poll(self):
        now = ticks_ms()
        if not self.link.wlan.isconnected():
            self.tokens = []
            self.remote_token = None
            self.pending = None
            return
        if self.role == "house":
            self.tokens = [(key, at) for key, at in self.tokens if ticks_diff(now, at) < 1000]
            if self.last_ready is None or ticks_diff(now, self.last_ready) >= 300:
                token = os.urandom(12).hex().encode()
                self.tokens.append((token, now))
                self.link.send(b"READY " + token)
                self.last_ready = now
        elif self.pending is not None:
            if ticks_diff(now, self.started) >= 800:
                self.pending = None
            elif self.last_send is None or ticks_diff(now, self.last_send) >= 200:
                self.link.send(self.pending[1])
                self.last_send = now


MODULE_VERSION = "0.6.1"
