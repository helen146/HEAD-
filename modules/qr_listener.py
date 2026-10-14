# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/qr_listener.py
Διαβάζει QR codes από την κάμερα USB (webcam) του Pi.

Τρέχει σε δικό του νήμα (thread) στο παρασκήνιο: κοιτά συνεχώς την
κάμερα, και μόλις δει QR με έγκυρο persona id, το βάζει σε ουρά για το
κύριο πρόγραμμα. Έτσι δεν «κολλάει» το πρόγραμμα περιμένοντας σκανάρισμα.

Το περιεχόμενο του QR είναι σκέτο κείμενο: το όνομα του αρχείου του
χαρακτήρα στο characters/, π.χ. "aristotelis", "arximidis", "theano".

Χρειάζεται:
    sudo apt install -y python3-opencv libzbar0
    pip install pyzbar
"""

import queue
import threading
import time

import config


class QRListener:
    def __init__(self, personas):
        self.personas = personas   # οι χαρακτήρες που φόρτωσε το prosopa.py
        self.events = queue.Queue()
        self._cap = None
        self._stop = threading.Event()
        self._last = ("", 0.0)   # (persona_id, χρόνος) — να μη διαβάζει ξανά το ίδιο

    def start(self):
        try:
            import cv2
            from pyzbar import pyzbar
        except ImportError as e:
            print(f"[QR] Λείπει βιβλιοθήκη ({e}) → συνεχίζω χωρίς QR.")
            return

        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self._cap.isOpened():
            print("[QR] Δεν άνοιξε η κάμερα → στη Φάση 1 άλλαξε persona με !1 / !2 / !3.")
            self._cap = None
            return

        # Χαμηλή ανάλυση = γρήγορη ανάγνωση· αρκεί για QR
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        def loop():
            while not self._stop.is_set():
                ok, frame = self._cap.read()
                if not ok:
                    time.sleep(0.2)
                    continue

                # Ασπρόμαυρη εικόνα → πιο γρήγορη και αξιόπιστη ανάγνωση
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                for code in pyzbar.decode(gray):
                    pid = code.data.decode("utf-8", errors="ignore").strip().lower()
                    if pid not in self.personas:
                        continue
                    # Το ίδιο QR μπροστά στην κάμερα δεν ξαναμετράει για 5 δευτ.
                    now = time.monotonic()
                    if pid == self._last[0] and now - self._last[1] < 5.0:
                        continue
                    self._last = (pid, now)
                    self.events.put(pid)
                    print(f"\n[QR] Σκαναρίστηκε: {self.personas[pid]['name']}")

                time.sleep(config.QR_SCAN_INTERVAL)

        threading.Thread(target=loop, daemon=True).start()
        print("[QR] Η κάμερα σαρώνει για QR codes ✓")

    def get_scanned(self):
        """Το πιο πρόσφατο persona id που σκαναρίστηκε, αλλιώς None."""
        pid = None
        while not self.events.empty():
            pid = self.events.get_nowait()
        return pid

    def close(self):
        self._stop.set()
        if self._cap:
            self._cap.release()
