# -*- coding: utf-8 -*-
"""
Κεφάλι AI — xrp/main.py  (MicroPython, τρέχει ΣΤΟ XRP)

Το XRP είναι ο «ελεγκτής κινήσεων»: δέχεται εντολές από το Raspberry Pi
μέσω USB σειριακής και κινεί τα σέρβο. ΚΑΘΟΛΟΥ AI εδώ — μόνο κίνηση.

Εντολές που καταλαβαίνει (μία ανά γραμμή):
    J:<0-255>           ένταση σιαγόνας → γωνία 0°–20° (θύρα servo 1)
    S:<θύρα>:<μοίρες>   οποιοδήποτε άλλο σέρβο, π.χ. S:2:45
    PING                απαντά PONG

Εγκατάσταση:
    Αποθήκευσε αυτό το αρχείο ως main.py στο XRP (με Thonny ή mpremote)
    → τρέχει αυτόματα σε κάθε εκκίνηση.
    ⚠️ Όσο τρέχει το πρόγραμμα από το Pi, το Thonny πρέπει να είναι
    ΚΛΕΙΣΤΟ — δεν μπορούν δύο προγράμματα να έχουν την ίδια θύρα.

Καλωδίωση:
    Σιαγόνα HK15298 → θύρα servo 1 του XRP
    Άλλα σέρβο      → θύρες servo 2, 3, 4
    XRP ↔ Pi        → καλώδιο USB-C (αυτό δίνει και τη σειριακή)
    ⚠️ Τα σέρβο τραβούν ρεύμα από την μπαταρία του XRP — για το HK15298
    (δυνατό servo) φρόντισε το XRP να τροφοδοτείται από μπαταρία,
    όχι μόνο από το USB.
"""

import sys
import select

from XRPLib.servo import Servo

# ─────────────────────────────
# ΡΥΘΜΙΣΕΙΣ (ίδιες λογικές με το config.py του Pi)
# ─────────────────────────────
JAW_SERVO_NUM = 1
JAW_CLOSED_DEG = 0.0
JAW_OPEN_DEG = 20.0
SMOOTHING = 0.6        # 0=καθόλου, 0.9=πολύ «μαλακή» κίνηση σιαγόνας

# ─────────────────────────────
# ΣΕΡΒΟ
# ─────────────────────────────
jaw = Servo.get_default_servo(JAW_SERVO_NUM)
_others = {}   # άλλα σέρβο, φορτώνονται όταν πρωτοζητηθούν


def get_servo(num):
    if num == JAW_SERVO_NUM:
        return jaw
    if num not in _others:
        _others[num] = Servo.get_default_servo(num)
    return _others[num]


_jaw_deg = JAW_CLOSED_DEG


def jaw_from_level(level_255):
    """Ένταση 0–255 → γωνία σιαγόνας, με λίγο «μαλάκωμα» (smoothing)
    ώστε η κίνηση να μη σπάει απότομα από καρέ σε καρέ."""
    global _jaw_deg
    target = JAW_CLOSED_DEG + (JAW_OPEN_DEG - JAW_CLOSED_DEG) * (level_255 / 255)
    _jaw_deg = SMOOTHING * _jaw_deg + (1 - SMOOTHING) * target
    jaw.set_angle(_jaw_deg)


def handle(line):
    line = line.strip()
    if not line:
        return
    try:
        if line.startswith("J:"):
            jaw_from_level(int(line[2:]))
        elif line.startswith("S:"):
            _, num, deg = line.split(":")
            get_servo(int(num)).set_angle(float(deg))
        elif line == "PING":
            print("PONG")
    except (ValueError, IndexError):
        pass  # χαλασμένη γραμμή → την αγνοούμε, δεν κολλάμε


# ─────────────────────────────
# ΚΥΡΙΟΣ ΒΡΟΧΟΣ: διάβασμα εντολών από τη USB σειριακή (stdin)
# ─────────────────────────────
jaw.set_angle(JAW_CLOSED_DEG)
print("KEFALI-XRP READY")

poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
buf = ""

while True:
    if poller.poll(20):  # περιμένουμε έως 20 ms για νέο χαρακτήρα
        ch = sys.stdin.read(1)
        if ch == "\n":
            handle(buf)
            buf = ""
        else:
            buf += ch
