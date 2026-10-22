"""One action per tag presentation, with confirmed absence before rearming."""

from time import ticks_diff


class TagPresence:
    def __init__(self):
        self.uid = None
        self.absent_since = None
        self.misses = 0

    def seen(self, uid):
        fresh = uid != self.uid
        self.uid = uid
        self.pause()
        return fresh

    def pause(self):
        # Reader recovery is not evidence that the physical tag was removed.
        self.absent_since = None
        self.misses = 0

    def missing(self, now):
        if self.absent_since is None:
            self.absent_since = now
        self.misses += 1
        if self.misses >= 4 and ticks_diff(now, self.absent_since) >= 800:
            self.uid = None


MODULE_VERSION = "0.5.0"
