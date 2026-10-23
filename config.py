# -*- coding: utf-8 -*-
"""
Κεφάλι AI — config.py
Όλες οι ρυθμίσεις του έργου σε ΕΝΑ σημείο.
Οι φιλόσοφοι ΔΕΝ είναι εδώ: ο καθένας είναι ένα αρχείο στο characters/
(δες README_PROSOPA.md).
"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

# ─────────────────────────────────────────────
# ΦΑΣΗ ΛΕΙΤΟΥΡΓΙΑΣ
# ─────────────────────────────────────────────
# 1 = πληκτρολόγιο (γράφεις την ερώτηση — μόνο για δοκιμές)
# 2 = μικρόφωνο + αναγνώριση ομιλίας (κανονική λειτουργία)
PHASE = 2

# Αν True, το πρόγραμμα τρέχει και σε laptop χωρίς XRP
# (η σιαγόνα απλώς τυπώνει τι ΘΑ έκανε).
SIMULATION_OK = True

# ─────────────────────────────────────────────
# ΚΛΕΙΔΙΑ API — δύο τρόποι (ΠΟΤΕ μέσα στον κώδικα):
#
#  Α) Μεταβλητές περιβάλλοντος:
#       export ANTHROPIC_API_KEY="sk-ant-..."
#       export ELEVENLABS_API_KEY="..."
#
#  Β) Αρχείο kleidia.txt δίπλα σε αυτό το config.py, με γραμμές:
#       ANTHROPIC_API_KEY=sk-ant-...
#       ELEVENLABS_API_KEY=...
#     (πρότυπο: kleidia.example.txt)
#     ⚠️ Το kleidia.txt ΔΕΝ το μοιράζεσαι / δεν το ανεβάζεις πουθενά!
#
# Το splitlines() και το strip() αφαιρούν και το κρυφό \r που αφήνουν
# τα Windows στο τέλος κάθε γραμμής — αλλιώς τα κλειδιά «δεν δουλεύουν».
# ─────────────────────────────────────────────
_kleidia = {}
_kleidia_file = PROJECT_DIR / "kleidia.txt"
if _kleidia_file.exists():
    for _line in _kleidia_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            _kleidia[_k.strip()] = _v.strip()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or _kleidia.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY") or _kleidia.get("ELEVENLABS_API_KEY", "")

# ─────────────────────────────────────────────
# ΜΟΝΤΕΛΑ
# ─────────────────────────────────────────────
ANTHROPIC_MODEL = "claude-haiku-5-5"         # online εγκέφαλος (ο πιο γρήγορος)
                                             # προηγούμενος: "claude-sonnet-4-6"
OLLAMA_MODEL = "llama3.2:3b"                 # offline εγκέφαλος (αρχικό σχέδιο —
OLLAMA_URL = "http://localhost:11434/api/chat"  # δεν χωράει στα 2 GB του Pi 4)
ELEVEN_MODEL = "eleven_flash_v2_5"           # online φωνή — πιο γρήγορη από
                                             # το eleven_multilingual_v2
WHISPER_SIZE = "base"                        # STT: το "small" ήταν πολύ αργό στο Pi 4
WHISPER_BEAM_SIZE = 1                        # 1 = γρήγορο · 5 = πιο προσεκτικό, πιο αργό

# Piper (offline φωνή, μία ελληνική φωνή για όλους).
# Ψάχνει στο ~/piper του χρήστη που τρέχει το πρόγραμμα — ΟΧΙ σε σταθερό
# /home/pi/ (αυτό ήταν το λάθος που κρατούσε τη φωνή σιωπηλή).
PIPER_DIR = Path.home() / "piper"
PIPER_MODEL = str(PIPER_DIR / "el_GR-rapunzelina-low.onnx")
PIPER_BIN = str(PIPER_DIR / "piper") if (PIPER_DIR / "piper").exists() else "piper"

# Έτοιμες φράσεις αναμονής («Χμμμ…»), φτιαγμένες μία φορά με ftiaxe_frasis.py
FRASIS_DIR = str(PROJECT_DIR / "audio_frasis")

# ─────────────────────────────────────────────
# XRP (ελεγκτής κινήσεων) — σύνδεση με USB σειριακή
# Το XRP εμφανίζεται στο Pi συνήθως ως /dev/ttyACM0
# ─────────────────────────────────────────────
XRP_SERIAL_PORT = "/dev/ttyACM0"
XRP_SERIAL_BAUD = 115200

# ─────────────────────────────────────────────
# ΣΙΑΓΟΝΑ (HK15298 στη θύρα servo 2 του XRP, εύρος 0°–20°)
# Οι άλλες θύρες: 1 = περιστροφή κεφαλιού, 3 = μάτια αριστερά–δεξιά,
# 4 = μάτια πάνω–κάτω. Οι θύρες ρυθμίζονται στο xrp/main.py.
# Οι μοίρες είναι αυτές που στέλνονται στο XRPLib set_angle().
# Ρύθμισε τα όρια ΠΡΟΣΕΚΤΙΚΑ με δοκιμή — λάθος όρια ζορίζουν τον μηχανισμό!
# ─────────────────────────────────────────────
JAW_SERVO_NUM = 2      # θύρα servo του XRP
JAW_CLOSED_DEG = 0     # γωνία «κλειστή σιαγόνα»
JAW_OPEN_DEG = 20      # γωνία «τελείως ανοιχτή»
JAW_FRAME_SEC = 0.05   # ανανέωση σιαγόνας κάθε 50 ms κατά την ομιλία

# ─────────────────────────────────────────────
# ΚΑΜΕΡΑ USB (σαρωτής QR)
# Το /dev/video0 αντιστοιχεί σε CAMERA_INDEX = 0
# ─────────────────────────────────────────────
CAMERA_INDEX = 0
QR_SCAN_INTERVAL = 0.15   # δευτ. ανάμεσα σε δύο σαρώσεις (χαμηλό = πιο γρήγορο)

# ─────────────────────────────────────────────
# ΜΙΚΡΟΦΩΝΟ — το μικρόφωνο της κάμερας USB
# Επιλέγεται με το ΟΝΟΜΑ της κάρτας ("Camera"), όχι με αριθμό:
# οι αριθμοί των καρτών ALSA αλλάζουν από boot σε boot, τα ονόματα όχι.
# Βρες τα ονόματα με:  arecord -l
# ─────────────────────────────────────────────
MIC_DEVICE = "plughw:Camera,0"

# --- Ανίχνευση φωνής (VAD) ---
# Το κεφάλι περιμένει σιωπηλά, ηχογραφεί μόλις ακούσει φωνή, και
# σταματά μόλις ο μαθητής σωπάσει.
MIC_THRESHOLD = 500      # αρχική ευαισθησία (0–32767). Ήσυχο δωμάτιο: 300–600.
                         # Θορυβώδης τάξη: 800–1500.
MIC_CALIBRATE = True     # True: στην εκκίνηση (και μετά από 30 δευτ. ησυχίας) το
                         # κεφάλι μετρά τον θόρυβο του δωματίου και βάζει μόνο του
                         # το κατώφλι. False: κρατά το MIC_THRESHOLD όπως είναι.
MIC_CALIBRATE_SEC = 2.0  # πόσα δευτ. ακούει το δωμάτιο στην εκκίνηση
MIC_CALIBRATE_FACTOR = 3.0   # κατώφλι = θόρυβος δωματίου × 3 (~10 dB πάνω)
MIC_THRESHOLD_MIN = 200  # όρια ασφαλείας για το αυτόματο κατώφλι
MIC_THRESHOLD_MAX = 2000
SILENCE_STOP_SEC = 1.2   # πόση σιωπή σημαίνει «τελείωσε η ερώτηση»
MAX_SPEECH_SEC = 15      # μέγιστη διάρκεια μιας ερώτησης
MAX_WAIT_SEC = 30        # αν δεν μιλήσει κανείς τόση ώρα, κάνει έναν κύκλο

# ─────────────────────────────────────────────
# ΦΙΛΟΣΟΦΟΙ
# Φορτώνονται από τα αρχεία characters/*.json (modules/prosopa.py).
# Το κείμενο κάθε QR code είναι το όνομα του αρχείου (π.χ. "aristotelis").
# ─────────────────────────────────────────────
DEFAULT_PERSONA = "aristotelis"

# Ιστορικό συζήτησης: πόσα ζεύγη ερώτηση/απάντηση κρατάμε
HISTORY_MAX_TURNS = 6
