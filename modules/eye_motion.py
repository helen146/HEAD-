"""Occasional eye glances on XRP Servos 3 and 4; no head movement."""

import random
import threading

import config


class EyeMotion:
    def __init__(self, xrp):
        self.xrp = xrp
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None

    def start(self):
        if not config.EYE_MOTION_ENABLED or not self.xrp.connected:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def glance_now(self):
        """Start a glance when a spoken clip begins."""
        if self._thread is not None and self._thread.is_alive():
            self._wake.set()

    def _run(self):
        axes = (
            (config.EYE_LR_SERVO_NUM, config.EYE_LR_CENTER_DEG,
             config.EYE_LR_GLANCE_DEG),
            (config.EYE_UD_SERVO_NUM, config.EYE_UD_CENTER_DEG,
             config.EYE_UD_GLANCE_DEG),
        )
        for port, center, _offset in axes:
            self.xrp.set_servo(port, center)

        while not self._stop.is_set():
            self._wake.wait(random.uniform(4.0, 7.0))
            self._wake.clear()
            if self._stop.is_set():
                break
            port, center, offset = random.choice(axes)
            self.xrp.set_servo(port, center + random.choice((-offset, offset)))
            if self._stop.wait(0.35):
                break
            self.xrp.set_servo(port, center)

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self.xrp.set_servo(config.EYE_LR_SERVO_NUM, config.EYE_LR_CENTER_DEG)
            self.xrp.set_servo(config.EYE_UD_SERVO_NUM, config.EYE_UD_CENTER_DEG)
