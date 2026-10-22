"""Call control with session IDs, heartbeat and answer/hangup state."""

import os
from time import ticks_ms, ticks_diff


def valid_id(value):
    return len(value) == 24 and all(c in b"0123456789abcdef" for c in value)


class Session:
    def __init__(self, link, chime, role):
        self.link = link
        self.chime = chime
        self.role = role
        self.call_id = None
        self.state = "IDLE"
        self.revision = -1
        self.changed = ticks_ms()
        self.last_heard = self.changed
        self.last_sent = None
        self.attempts = 0
        self.closed = []
        self.voice = None

    def transition(self, state):
        self.state = state
        self.changed = ticks_ms()
        self.last_sent = None
        if state != "TALKING" and self.voice is not None and self.voice.running:
            self.voice.stop()
        print("CALL STATE:", state)
        if state == "RINGING":
            self.chime.ring(repeat=True)
        elif state in ("IDLE", "TALKING"):
            self.chime.stop()

    def finish(self):
        if self.call_id is not None:
            self.closed.append(self.call_id)
            self.closed = self.closed[-32:]
        self.transition("IDLE")
        self.call_id = None

    def call(self):
        if self.call_id is not None:
            print("Call already active; gate press ignored")
            return
        if not self.link.wlan.isconnected():
            print("No WiFi; call not queued")
            return
        self.call_id = os.urandom(12).hex().encode()
        self.revision = -1
        self.attempts = 0
        self.last_heard = ticks_ms()
        self.transition("CALLING")

    def talk_button(self):
        if self.state == "RINGING":
            self.revision += 1
            self.transition("TALKING")
        elif self.state == "TALKING":
            self.end()
        else:
            print("No incoming call; talk press ignored")

    def end(self):
        if self.role == "house" and self.call_id is not None and self.state != "IDLE":
            self.revision += 1
            self.transition("IDLE")

    def receive(self, packet):
        parts = packet.split()
        now = ticks_ms()
        if self.role == "house":
            if len(parts) == 2 and parts[0] == b"CALL" and valid_id(parts[1]):
                key = parts[1]
                if key == self.call_id:
                    self.last_heard = now
                    self.last_sent = None
                elif key not in self.closed and self.state == "IDLE":
                    if self.call_id is not None:
                        self.closed.append(self.call_id)
                        self.closed = self.closed[-32:]
                    self.call_id = key
                    self.revision = 0
                    self.last_heard = now
                    self.transition("RINGING")
            elif len(parts) == 2 and parts[0] == b"PING" and parts[1] == self.call_id:
                self.last_heard = now
        elif len(parts) == 4 and parts[0] == b"STATE" and parts[1] == self.call_id:
            if parts[3] not in (b"RINGING", b"TALKING", b"IDLE"):
                return
            try:
                revision = int(parts[2])
            except ValueError:
                return
            if revision < self.revision:
                return
            self.last_heard = now
            if revision > self.revision:
                self.revision = revision
                state = parts[3].decode()
                if state == "IDLE":
                    self.finish()
                else:
                    self.transition(state)

    def poll(self):
        now = ticks_ms()
        if self.call_id is None:
            return
        if self.role == "house":
            limit = 30000 if self.state == "RINGING" else 120000
            if self.state != "IDLE" and (ticks_diff(now, self.changed) >= limit or
                                         ticks_diff(now, self.last_heard) >= 3000):
                print("Call timeout or peer lost")
                self.end()
            if self.state == "IDLE" and ticks_diff(now, self.changed) >= 5000:
                self.finish()
                return
            if self.last_sent is None or ticks_diff(now, self.last_sent) >= 500:
                self.link.send(b"STATE " + self.call_id + b" " +
                               str(self.revision).encode() + b" " + self.state.encode())
                self.last_sent = now
        else:
            if ticks_diff(now, self.last_heard) >= 3000:
                print("House unreachable; call ended")
                self.finish()
                return
            if self.last_sent is None or ticks_diff(now, self.last_sent) >= 500:
                if self.state == "CALLING":
                    if self.attempts >= 4:
                        print("No call confirmation")
                        self.finish()
                        return
                    self.link.send(b"CALL " + self.call_id)
                    self.attempts += 1
                else:
                    self.link.send(b"PING " + self.call_id)
                self.last_sent = now


MODULE_VERSION = "0.6.1"
