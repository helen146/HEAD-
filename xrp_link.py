# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/xrp_link.py
Η «γέφυρα» Pi → XRP: όλες οι κινήσεις γίνονται στο XRP, το Pi απλώς
στέλνει εντολές μέσω USB σειριακής (καλώδιο USB-C στο XRP).

Πρωτόκολλο (γραμμές κειμένου, τελειώνουν με \\n):
    J:<0-255>          ένταση σιαγόνας για το τρέχον καρέ (0=κλειστή)
    S:<θύρα>:<μοίρες>  οποιοδήποτε άλλο σέρβο (π.χ. S:2:45)
    PING               το XRP απαντά PONG (έλεγχος ζωής)

Ο συγχρονισμός σιαγόνας-φωνής:
    Ο ήχος παίζει ΣΤΟ PI (ηχείο στο Pi). Το WAV χωρίζεται σε καρέ των
    50 ms, υπολογίζεται η ένταση (RMS) κάθε καρέ, και την ώρα της
    αναπαραγωγής στέλνεται ένα J:<ένταση> ανά καρέ. Το XRP απλώς
    μετατρέπει την ένταση σε γωνία — μηδενικός φόρτος για το RP2350.

Χρειάζεται: pip install pyserial
"""

import subprocess
import time
import wave

import config


class XRPLink:
    def __init__(self):
        self._ser = None
        try:
            import serial
            self._ser = serial.Serial(
                config.XRP_SERIAL_PORT, config.XRP_SERIAL_BAUD, timeout=1
            )
            time.sleep(2)  # το XRP κάνει επανεκκίνηση όταν ανοίγει η θύρα
            self._ser.reset_input_buffer()
            print(f"[XRP] Συνδέθηκα στη θύρα {config.XRP_SERIAL_PORT} ✓")
        except Exception as e:
            if not config.SIMULATION_OK:
                raise
            print(f"[XRP] Δεν βρέθηκε XRP ({e}) → λειτουργία προσομοίωσης.")

    # ---------- βασική αποστολή ----------
    def _send(self, line: str):
        if self._ser:
            try:
                self._ser.write((line + "\n").encode("ascii"))
            except Exception as e:
                print(f"[XRP] Σφάλμα αποστολής: {e}")

    # ---------- δημόσιες εντολές ----------
    def jaw_level(self, level: float):
        """level 0.0–1.0 → ένταση σιαγόνας (το XRP τη μετατρέπει σε γωνία)."""
        self._send(f"J:{int(max(0.0, min(1.0, level)) * 255)}")

    def set_servo(self, num: int, degrees: float):
        """Οποιοδήποτε άλλο σέρβο του XRP (θύρες 2, 3, 4…)."""
        self._send(f"S:{num}:{degrees:.1f}")

    def close(self):
        self.jaw_level(0)
        time.sleep(0.2)
        if self._ser:
            self._ser.close()


# ─────────────────────────────────────────────
# Ανάλυση πλάτους + αναπαραγωγή με συγχρονισμό
# ─────────────────────────────────────────────
def wav_envelope(wav_path: str, frame_sec: float = None) -> list:
    """Λίστα τιμών 0.0–1.0, μία ανά καρέ των 50 ms (ένταση φωνής)."""
    frame_sec = frame_sec or config.JAW_FRAME_SEC
    with wave.open(wav_path, "rb") as w:
        rate, nch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())

    if width != 2:
        return []  # περιμένουμε 16-bit· τα WAV μας είναι πάντα έτσι

    import array
    samples = array.array("h", raw)
    if nch > 1:
        samples = samples[::nch]  # κρατάμε το 1ο κανάλι

    per_frame = max(1, int(rate * frame_sec))
    env = []
    for i in range(0, len(samples), per_frame):
        chunk = samples[i : i + per_frame]
        if not chunk:
            break
        rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
        env.append(rms)

    peak = max(env) if env else 1.0
    if peak <= 0:
        peak = 1.0
    # Κανονικοποίηση + κατώφλι ώστε ο θόρυβος να μην ανοίγει τη σιαγόνα
    return [0.0 if (v / peak) < 0.08 else (v / peak) for v in env]


def play_with_jaw(wav_path: str, xrp: XRPLink):
    """Παίζει το WAV στο ηχείο του Pi και στέλνει την ένταση κάθε καρέ
    στο XRP — η σιαγόνα «κουνιέται στον ρυθμό» της φωνής."""
    if not wav_path:
        return
    env = wav_envelope(wav_path)
    proc = subprocess.Popen(["aplay", "-q", wav_path])
    t0 = time.monotonic()
    for i, level in enumerate(env):
        xrp.jaw_level(level)
        # Κοιμόμαστε μέχρι την ΑΠΟΛΥΤΗ ώρα του επόμενου καρέ (όχι σκέτο sleep)
        target = t0 + (i + 1) * config.JAW_FRAME_SEC
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)
    xrp.jaw_level(0)
    proc.wait()
