# -*- coding: utf-8 -*-
"""
Κεφάλι AI — xrp/main.py  (MicroPython, τρέχει ΣΤΟ XRP)

Το XRP είναι ο «ελεγκτής κινήσεων»: δέχεται εντολές από το Raspberry Pi
μέσω USB σειριακής και κινεί τα σέρβο. ΚΑΘΟΛΟΥ AI εδώ — μόνο κίνηση.

Εντολές που καταλαβαίνει (μία ανά γραμμή):
    J:<0-255>           ένταση σιαγόνας → γωνία 0°–20° (θύρα servo 2)
    S:<θύρα>:<μοίρες>   οποιοδήποτε σέρβο, π.χ. S:3:60 (μάτια στο κέντρο)
    PING                απαντά PONG

Εγκατάσταση:
    Αποθήκευσε αυτό το αρχείο ως main.py στο XRP (με Thonny ή mpremote)
    → τρέχει αυτόματα σε κάθε εκκίνηση.
    ⚠️ Όσο τρέχει το πρόγραμμα από το Pi, το Thonny πρέπει να είναι
    ΚΛΕΙΣΤΟ — δεν μπορούν δύο προγράμματα να έχουν την ίδια θύρα.

Καλωδίωση:
    Θύρα servo 1 → περιστροφή κεφαλιού (αριστερά–δεξιά)
    Θύρα servo 2 → σιαγόνα HK15298 (άνοιγμα–κλείσιμο)
    Θύρα servo 3 → μάτια αριστερά–δεξιά
    Θύρα servo 4 → μάτια πάνω–κάτω
    XRP ↔ Pi     → καλώδιο USB-C (αυτό δίνει και τη σειριακή)
    ⚠️ Τα σέρβο τραβούν ρεύμα από την μπαταρία του XRP — φρόντισε το XRP
    να τροφοδοτείται από μπαταρία, όχι μόνο από το USB.
"""

import sys
import select

from XRPLib.servo import Servo

# ─────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────
HEAD_SERVO_NUM = 1     # περιστροφή κεφαλιού
JAW_SERVO_NUM = 2      # σιαγόνα (πριν ήταν στη θύρα 1)
EYES_LR_SERVO_NUM = 3  # μάτια αριστερά–δεξιά
EYES_UD_SERVO_NUM = 4  # μάτια πάνω–κάτω

JAW_CLOSED_DEG = 0.0
JAW_OPEN_DEG = 20.0    # το τεστ κινήσεων φτάνει ως 35° — άλλαξέ το αν το επιβεβαιώσεις
SMOOTHING = 0.6        # 0=καθόλου, 0.9=πολύ «μαλακή» κίνηση σιαγόνας

# Ουδέτερη θέση στην εκκίνηση: κεφάλι και μάτια κοιτάνε ευθεία
# (τα κέντρα του τεστ κινήσεων).
NEUTRAL_DEG = {
    HEAD_SERVO_NUM: 90.0,
    EYES_LR_SERVO_NUM: 60.0,
    EYES_UD_SERVO_NUM: 90.0,
}

# Ασφαλή όρια ανά θύρα (από το τεστ κινήσεων). Κάθε εντολή κόβεται σε
# αυτά, ώστε λάθος τιμή να μη ζορίσει ποτέ τον μηχανισμό.
LIMITS_DEG = {
    HEAD_SERVO_NUM: (45.0, 135.0),
    JAW_SERVO_NUM: (0.0, 35.0),
    EYES_LR_SERVO_NUM: (10.0, 110.0),
    EYES_UD_SERVO_NUM: (45.0, 135.0),
}

# ─────────────────────────────
# ΣΕΡΒΟ
# ─────────────────────────────
_servos = {}   # φορτώνονται όταν πρωτοζητηθούν


def get_servo(num):
    if num not in _servos:
        _servos[num] = Servo.get_default_servo(num)
    return _servos[num]


def set_angle(num, deg):
    """Κινεί ένα σέρβο, πάντα μέσα στα ασφαλή του όρια."""
    lo, hi = LIMITS_DEG.get(num, (0.0, 180.0))
    get_servo(num).set_angle(max(lo, min(hi, deg)))


_jaw_deg = JAW_CLOSED_DEG


def jaw_from_level(level_255):
    """Ένταση 0–255 → γωνία σιαγόνας, με λίγο «μαλάκωμα» (smoothing)
    ώστε η κίνηση να μη σπάει απότομα από καρέ σε καρέ."""
    global _jaw_deg
    target = JAW_CLOSED_DEG + (JAW_OPEN_DEG - JAW_CLOSED_DEG) * (level_255 / 255)
    _jaw_deg = SMOOTHING * _jaw_deg + (1 - SMOOTHING) * target
    set_angle(JAW_SERVO_NUM, _jaw_deg)


def handle(line):
    line = line.strip()
    if not line:
        return
    try:
        if line.startswith("J:"):
            jaw_from_level(int(line[2:]))
        elif line.startswith("S:"):
            _, num, deg = line.split(":")
            set_angle(int(num), float(deg))
        elif line == "PING":
            print("PONG")
    except (ValueError, IndexError):
        pass  # χαλασμένη γραμμή → την αγνοούμε, δεν κολλάμε


# ─────────────────────────────
# ΕΚΚΙΝΗΣΗ: στόμα κλειστό, κεφάλι και μάτια ευθεία
# ─────────────────────────────
set_angle(JAW_SERVO_NUM, JAW_CLOSED_DEG)
for _num, _deg in NEUTRAL_DEG.items():
    set_angle(_num, _deg)
print("KEFALI-XRP READY")

# ─────────────────────────────
# ΚΥΡΙΟΣ ΒΡΟΧΟΣ: διάβασμα εντολών από τη USB σειριακή (stdin)
# ─────────────────────────────
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
