# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/ears.py
Τα «αυτιά»: πώς μπαίνει η ερώτηση του μαθητή.

  • Φάση 1 → πληκτρολόγιο
  • Φάση 2 → μικρόφωνο της κάμερας USB + faster-whisper (τοπικά, χωρίς internet)

ΠΩΣ ΑΚΟΥΕΙ (Φάση 2):
    Το κεφάλι ΔΕΝ ηχογραφεί «στα τυφλά» για Χ δευτερόλεπτα:
      1. Ακούει σιωπηλά και περιμένει να αρχίσει κάποιος να μιλά
      2. Μόλις πιάσει φωνή, ηχογραφεί (κρατώντας και λίγο ΠΡΙΝ, ώστε να
         μη χαθεί η πρώτη συλλαβή)
      3. Μόλις ο μαθητής σωπάσει (~1.2 δευτ.), σταματά
    Χωρίς κουμπιά, χωρίς χρονόμετρα, χωρίς βρόχους σε άδειο δωμάτιο.

ΚΑΤΩΦΛΙ ΦΩΝΗΣ ΠΟΥ ΡΥΘΜΙΖΕΤΑΙ ΜΟΝΟ ΤΟΥ:
    Στην εκκίνηση το κεφάλι ακούει το δωμάτιο 2 δευτ. και βάζει το κατώφλι
    φωνής ~3 φορές πάνω από τον θόρυβο του δωματίου. Ήσυχο δωμάτιο → πιο
    ευαίσθητο (ακούει και τα παιδιά που μιλούν σιγά ή από μακριά).
    Θορυβώδες → λιγότερο ευαίσθητο (δεν ξεκινά να γράφει με το πρώτο θρόισμα).
    Ξαναρυθμίζεται μετά από κάθε ήσυχη αναμονή 30 δευτ.

ΓΙΑ ΚΑΛΥΤΕΡΗ ΑΚΡΙΒΕΙΑ:
    • Μοντέλο "base": το "tiny" έκανε λάθη στα ελληνικά, το "small" ήταν
      πολύ αργό στο Pi 4 — το "base" είναι η ισορροπία
    • Κανονικοποίηση έντασης: αν μιλάς σιγά, ο ήχος ενισχύεται πριν
      φτάσει στο whisper
    • initial_prompt στα ελληνικά: «προθερμαίνει» το μοντέλο ώστε να
      περιμένει ελληνικά ΚΑΙ φιλοσοφικό λεξιλόγιο (ονόματα, όροι)
    • beam_size=1: πιο γρήγορο (5 = πιο προσεκτικό, πιο αργό)

ΟΛΕΣ οι ρυθμίσεις έχουν προεπιλογές ΕΔΩ — δεν χρειάζεται αλλαγή στο
config.py. Αν όμως ορίσεις κάτι στο config, εκείνο υπερισχύει.
"""

import array
import math
import subprocess
import time
import wave

import config

TMP_REC = "/tmp/kefali_question.wav"

RATE = 16000
CHUNK_MS = 100
CHUNK_BYTES = RATE * CHUNK_MS // 1000 * 2   # 16-bit mono


# ── Ρυθμίσεις με προεπιλογές (το config υπερισχύει αν τις ορίζει) ──
def _cfg(name, default):
    return getattr(config, name, default)


MIC_DEVICE = _cfg("MIC_DEVICE", "plughw:Camera,0")   # με ΟΝΟΜΑ κάρτας, όχι αριθμό
WHISPER_SIZE = _cfg("WHISPER_SIZE", "base")
MIC_THRESHOLD = _cfg("MIC_THRESHOLD", 500)     # αρχική ευαισθησία (0–32767)
MIC_CALIBRATE = _cfg("MIC_CALIBRATE", True)    # ρύθμιση κατωφλιού από τον θόρυβο του δωματίου
MIC_CALIBRATE_SEC = _cfg("MIC_CALIBRATE_SEC", 2.0)        # πόσο ακούει στην εκκίνηση
MIC_CALIBRATE_FACTOR = _cfg("MIC_CALIBRATE_FACTOR", 3.0)  # κατώφλι = θόρυβος × 3 (~+10 dB)
MIC_THRESHOLD_MIN = _cfg("MIC_THRESHOLD_MIN", 200)        # ποτέ πιο ευαίσθητο από αυτό
MIC_THRESHOLD_MAX = _cfg("MIC_THRESHOLD_MAX", 2000)       # ποτέ λιγότερο ευαίσθητο από αυτό
SILENCE_STOP_SEC = _cfg("SILENCE_STOP_SEC", 1.2)
MAX_SPEECH_SEC = _cfg("MAX_SPEECH_SEC", 15)
MAX_WAIT_SEC = _cfg("MAX_WAIT_SEC", 30)
WHISPER_BEAM_SIZE = _cfg("WHISPER_BEAM_SIZE", 1)   # 1 = γρήγορο, 5 = πιο προσεκτικό

# «Προθέρμανση» του μοντέλου: του λέμε τι είδους ελληνικά να περιμένει.
# Βοηθά πολύ με ονόματα και όρους που αλλιώς τα ακούει λάθος.
# Τα ονόματα των φιλοσόφων έρχονται από τα αρχεία characters/, οπότε
# ένας νέος χαρακτήρας «διδάσκει» αυτόματα και το όνομά του στο whisper.
HINT_INTRO = "Ερωτήσεις μαθητών προς αρχαίους Έλληνες φιλοσόφους. "
HINT_DEFAULT_NAMES = "Αριστοτέλης, Αρχιμήδης, Θεανώ. "
HINT_EXTRA = (
    "Πυθαγόρας, Πλάτωνας, Σωκράτης. "
    "Φιλοσοφία, μαθηματικά, ευτυχία, αρετή, γεωμετρία, αριθμοί, μοχλός."
)


def _rms(raw: bytes) -> float:
    if len(raw) < 2:
        return 0.0
    samples = array.array("h", raw[: len(raw) // 2 * 2])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def _room_floor(levels):
    """Ο «θόρυβος του δωματίου»: το 30ό εκατοστημόριο των εντάσεων.
    Μια φωνή ή ένας χτύπος στη μέση της μέτρησης δεν τον ανεβάζουν."""
    if not levels:
        return None
    s = sorted(levels)
    return s[int(len(s) * 0.3)]


def _threshold_for(floor: float) -> float:
    return max(MIC_THRESHOLD_MIN, min(MIC_THRESHOLD_MAX, floor * MIC_CALIBRATE_FACTOR))


def _normalize(raw: bytes) -> bytes:
    """Ανεβάζει την ένταση σε καλό επίπεδο (αν μίλησε κάποιος σιγά).
    Το whisper ακούει ΠΟΛΥ καλύτερα καθαρό, δυνατό ήχο."""
    samples = array.array("h", raw[: len(raw) // 2 * 2])
    if not samples:
        return raw
    peak = max(abs(s) for s in samples)
    if peak == 0:
        return raw
    gain = min(20000 / peak, 8.0)   # στόχος ~60% κλίμακας, το πολύ 8× ενίσχυση
    if gain <= 1.05:
        return raw                  # ήταν ήδη αρκετά δυνατός
    for i, s in enumerate(samples):
        v = int(s * gain)
        samples[i] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
    return samples.tobytes()


class Ears:
    def __init__(self, names_hint=None):
        self._whisper = None
        self.last_stt_sec = None   # πόσο κράτησε η τελευταία αναγνώριση
        self.threshold = float(MIC_THRESHOLD)   # το κατώφλι φωνής που ισχύει τώρα
        self.room_floor = None                  # ο θόρυβος του δωματίου, όταν μετρηθεί
        self._hint = HINT_INTRO + (names_hint or HINT_DEFAULT_NAMES) + HINT_EXTRA

    # ---------- Κατώφλι φωνής από τον θόρυβο του δωματίου ----------
    def calibrate(self):
        """Ακούει το δωμάτιο λίγα δευτερόλεπτα (πριν μιλήσει ο φιλόσοφος)
        και ρυθμίζει το κατώφλι φωνής. Αν κάτι πάει στραβά, κρατά την
        τιμή του config.py — η ακρόαση δουλεύει όπως πριν."""
        if config.PHASE < 2 or not MIC_CALIBRATE:
            return
        n = max(5, int(MIC_CALIBRATE_SEC * 1000 / CHUNK_MS))
        levels = []
        try:
            proc = subprocess.Popen(
                ["arecord", "-q", "-D", MIC_DEVICE,
                 "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
                stdout=subprocess.PIPE,
            )
            try:
                for _ in range(n + 2):
                    chunk = proc.stdout.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    levels.append(_rms(chunk))
            finally:
                proc.terminate()
                proc.wait()
        except Exception as e:
            print(f"[Ears] Δεν μέτρησα τον θόρυβο ({e}) — κρατώ κατώφλι {self.threshold:.0f}.")
            return
        # Τα 2 πρώτα καρέ (0.2 δευτ.) τα πετάμε: η κάρτα ήχου «ξυπνά» με κλικ
        self._set_from_levels(levels[2:], "εκκίνηση")

    def _set_from_levels(self, levels, why: str):
        if len(levels) < 5:
            return
        floor = _room_floor(levels)
        old = self.threshold
        self.room_floor = floor
        self.threshold = _threshold_for(floor)
        print(f"[Ears] Θόρυβος δωματίου ≈ {floor:.0f} → κατώφλι φωνής {self.threshold:.0f} "
              f"(ήταν {old:.0f}, {why})")

    def warmup(self):
        if config.PHASE < 2 or self._whisper is not None:
            return
        print(f"[Ears] Φορτώνω το μοντέλο ακρόασης «{WHISPER_SIZE}» (μία φορά)…")
        from faster_whisper import WhisperModel
        self._whisper = WhisperModel(
            WHISPER_SIZE, device="cpu", compute_type="int8", cpu_threads=4
        )
        print("[Ears] Έτοιμο ✓")

    # ---------- Δημόσια συνάρτηση ----------
    def listen(self, qr=None) -> str:
        """Αν δοθεί το qr (QRListener), η ακρόαση ΔΙΑΚΟΠΤΕΤΑΙ μόλις η κάμερα
        δει QR code — έτσι ο νέος φιλόσοφος συστήνεται αμέσως, χωρίς να
        περιμένει να τελειώσει η ερώτηση."""
        if config.PHASE >= 2:
            return self._listen_microphone(qr)
        return input("❓ Ερώτηση (Enter για έξοδο): ").strip()

    # ---------- Φάση 2 ----------
    def _listen_microphone(self, qr=None) -> str:
        raw = self._record_until_silence(qr)
        if raw is None:
            return ""
        t_start = time.monotonic()

        raw = _normalize(raw)
        with wave.open(TMP_REC, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(raw)

        self.warmup()
        print("[Ears] Καταλαβαίνω τι είπες…")
        segments, _ = self._whisper.transcribe(
            TMP_REC,
            language="el",
            beam_size=WHISPER_BEAM_SIZE,    # 1 = πιο γρήγορο (δες config.py)
            without_timestamps=True,        # δεν χρειαζόμαστε χρόνους λέξεων
            initial_prompt=self._hint,      # «περίμενε ελληνικά, φιλοσοφία»
            condition_on_previous_text=False,
            vad_filter=True,
            temperature=0.0,                # χωρίς τυχαιότητα → σταθερά αποτελέσματα
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        self.last_stt_sec = time.monotonic() - t_start

        if not text:
            print("[Ears] Δεν κατάλαβα — ξαναπές το πιο καθαρά.")
            return ""

        print(f"📝 Άκουσα: «{text}»")
        return text

    def _record_until_silence(self, qr=None):
        """Περιμένει φωνή, ηχογραφεί, σταματά στη σιωπή.
        Επιστρέφει raw bytes, ή None αν δεν μίλησε κανείς / σκαναρίστηκε QR."""
        proc = subprocess.Popen(
            ["arecord", "-q", "-D", MIC_DEVICE,
             "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
            stdout=subprocess.PIPE,
        )

        speech = bytearray()
        pre_roll = []          # κρατάμε τα τελευταία καρέ ΠΡΙΝ αρχίσει η φωνή
        wait_levels = []       # οι εντάσεις όσο περιμένουμε (για νέα ρύθμιση κατωφλιού)
        speaking = False
        silence_chunks = 0
        waited_chunks = 0
        threshold = self.threshold

        max_silence = int(SILENCE_STOP_SEC * 1000 / CHUNK_MS)
        max_speech = int(MAX_SPEECH_SEC * 1000 / CHUNK_MS)
        max_wait = int(MAX_WAIT_SEC * 1000 / CHUNK_MS)

        print("🎤 Ακούω… (μίλα όποτε θέλεις)")
        try:
            while True:
                # Σκαναρίστηκε QR; → σταμάτα την ακρόαση αμέσως
                if qr is not None and not qr.events.empty():
                    return None

                chunk = proc.stdout.read(CHUNK_BYTES)
                if not chunk:
                    break
                level = _rms(chunk)

                if not speaking:
                    # Κρατάμε τα 3 τελευταία καρέ (0.3 δευτ.) — έτσι δεν χάνεται
                    # η πρώτη συλλαβή όταν αρχίσει να μιλά
                    pre_roll.append(chunk)
                    if len(pre_roll) > 3:
                        pre_roll.pop(0)

                    waited_chunks += 1
                    wait_levels.append(level)
                    if level > threshold:
                        speaking = True
                        for c in pre_roll:
                            speech.extend(c)
                        print("   …σε ακούω", flush=True)
                    elif waited_chunks > max_wait:
                        # 30 δευτ. χωρίς φωνή: καλή στιγμή να ξαναμετρήσουμε το δωμάτιο
                        if MIC_CALIBRATE:
                            self._set_from_levels(wait_levels, "μετά από ήσυχη αναμονή")
                        return None
                else:
                    speech.extend(chunk)
                    if level < threshold:
                        silence_chunks += 1
                        if silence_chunks >= max_silence:
                            break
                    else:
                        silence_chunks = 0
                    if len(speech) // CHUNK_BYTES > max_speech:
                        break
        finally:
            proc.terminate()
            proc.wait()

        if len(speech) < CHUNK_BYTES * 5:   # < 0.5 δευτ. → μάλλον θόρυβος
            return None
        return bytes(speech)
