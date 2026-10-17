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

ΓΙΑ ΚΑΛΥΤΕΡΗ ΑΚΡΙΒΕΙΑ:
    • Μοντέλο "base": το "tiny" έκανε λάθη στα ελληνικά, το "small" ήταν
      πολύ αργό στο Pi 4 — το "base" είναι η ισορροπία
    • Κανονικοποίηση έντασης: αν μιλάς σιγά, ο ήχος ενισχύεται πριν
      φτάσει στο whisper
    • initial_prompt στα ελληνικά: «προθερμαίνει» το μοντέλο ώστε να
      περιμένει ελληνικά ΚΑΙ φιλοσοφικό λεξιλόγιο (ονόματα, όροι)
    • beam_size=5: ψάχνει περισσότερες πιθανές ερμηνείες (πιο ακριβές)

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
STT_PROVIDER = _cfg("STT_PROVIDER", "whisper")
MIC_THRESHOLD = _cfg("MIC_THRESHOLD", 500)     # ευαισθησία (0–32767)
MIC_START_CHUNKS = _cfg("MIC_START_CHUNKS", 1)
SILENCE_STOP_SEC = _cfg("SILENCE_STOP_SEC", 1.2)
MAX_SPEECH_SEC = _cfg("MAX_SPEECH_SEC", 15)
MAX_WAIT_SEC = _cfg("MAX_WAIT_SEC", 30)
WHISPER_BEAM_SIZE = _cfg("WHISPER_BEAM_SIZE", 1)   # 1 = γρήγορο, 5 = πιο προσεκτικό

# «Προθέρμανση» του μοντέλου: του λέμε τι είδους ελληνικά να περιμένει.
# Βοηθά πολύ με ονόματα και όρους που αλλιώς τα ακούει λάθος.
# Τα ονόματα των φιλοσόφων έρχονται από τα αρχεία characters/, οπότε
# ένας νέος χαρακτήρας «διδάσκει» αυτόματα και το όνομά του στο whisper.
HINT_DEFAULT_NAMES = "Αριστοτέλης, Αρχιμήδης, Θεανώ. "
HINT_EXTRA = "Αριστοτέλη, πώς σε λένε; Αρχιμήδη, πώς σε λένε; Θεανώ, πώς σε λένε;"



def _rms(raw: bytes) -> float:
    if len(raw) < 2:
        return 0.0
    samples = array.array("h", raw[: len(raw) // 2 * 2])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


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
        self._hint = (names_hint or HINT_DEFAULT_NAMES) + HINT_EXTRA
        if STT_PROVIDER == "elevenlabs":
            print("[Ears] Αναγνώριση: ElevenLabs Scribe v2 (ελληνικά)")

    def warmup(self, force=False):
        if config.PHASE < 2 or self._whisper is not None:
            return
        if STT_PROVIDER == "elevenlabs" and not force:
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

        print("[Ears] Καταλαβαίνω τι είπες…")
        if STT_PROVIDER == "elevenlabs":
            try:
                text = self._transcribe_elevenlabs(TMP_REC)
            except Exception as exc:
                print(f"[Ears] ElevenLabs failed ({type(exc).__name__}); using local Whisper.")
                text = self._transcribe_whisper(TMP_REC)
        else:
            text = self._transcribe_whisper(TMP_REC)
        self.last_stt_sec = time.monotonic() - t_start

        words = [word.casefold().strip(".,!?;:«»") for word in text.split()]
        if len(words) < 2 or (len(words) >= 10 and len(set(words)) <= len(words) // 3):
            print("[Ears] Δεν κατάλαβα — ξαναπές το πιο καθαρά.")
            return ""

        print(f"📝 Άκουσα: «{text}»")
        return text

    def _transcribe_elevenlabs(self, path):
        import requests

        if not config.ELEVENLABS_API_KEY:
            raise RuntimeError("ElevenLabs API key unavailable")
        with open(path, "rb") as audio:
            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY},
                data={"model_id": "scribe_v2", "language_code": "ell", "tag_audio_events": "false"},
                files={"file": ("question.wav", audio, "audio/wav")},
                timeout=(3, 12),
            )
        response.raise_for_status()
        return response.json()["text"].strip()

    def _transcribe_whisper(self, path):
        self.warmup(force=True)
        segments, _ = self._whisper.transcribe(
            path,
            language="el",
            beam_size=WHISPER_BEAM_SIZE,
            without_timestamps=True,
            max_new_tokens=64,
            no_repeat_ngram_size=3,
            repetition_penalty=1.1,
            initial_prompt=self._hint,
            condition_on_previous_text=False,
            vad_filter=True,
            temperature=0.0,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

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
        speaking = False
        silence_chunks = 0
        waited_chunks = 0
        start_chunks = 0

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
                    start_chunks = start_chunks + 1 if level > MIC_THRESHOLD else 0
                    if start_chunks >= MIC_START_CHUNKS:
                        speaking = True
                        for c in pre_roll:
                            speech.extend(c)
                        print("   …σε ακούω", flush=True)
                    elif waited_chunks > max_wait:
                        return None
                else:
                    speech.extend(chunk)
                    if level < MIC_THRESHOLD:
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
