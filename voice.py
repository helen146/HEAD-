# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/voice.py
Η «φωνή» (TTS): μετατρέπει το κείμενο της απάντησης σε αρχείο WAV.

Δύο μηχανές πίσω από την ΙΔΙΑ συνάρτηση speak_to_wav():
  • Online  → ElevenLabs (ξεχωριστή ελληνική φωνή ανά φιλόσοφο)
  • Offline → Piper (μία ελληνική φωνή για όλους — δίχτυ ασφαλείας)

Σημείωση: για τη μετατροπή MP3→WAV χρειάζεται ffmpeg:
  sudo apt install ffmpeg
"""

import subprocess
import urllib.request

import config

TMP_MP3 = "/tmp/kefali_answer.mp3"
TMP_WAV = "/tmp/kefali_answer.wav"


class Voice:
    # ---------- Δημόσια συνάρτηση ----------
    def speak_to_wav(self, text: str, voice_id: str, online: bool) -> str:
        """Επιστρέφει τη διαδρομή ενός WAV (mono, 22050 Hz, 16-bit)."""
        if online and config.ELEVENLABS_API_KEY and voice_id and "BALE" not in voice_id:
            try:
                return self._elevenlabs(text, voice_id)
            except Exception as e:
                print(f"[Voice] Το ElevenLabs απέτυχε ({e}) → δοκιμάζω Piper…")
        return self._piper(text)

    # ---------- Online: ElevenLabs ----------
    def _elevenlabs(self, text: str, voice_id: str) -> str:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
        body = {
            "text": text,
            "model_id": config.ELEVEN_MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        import json
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            audio = r.read()
        with open(TMP_MP3, "wb") as f:
            f.write(audio)
        # MP3 → WAV mono 22050 Hz (για ανάλυση πλάτους + απλή αναπαραγωγή)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", TMP_MP3,
             "-ac", "1", "-ar", "22050", "-sample_fmt", "s16", TMP_WAV],
            check=True,
        )
        return TMP_WAV

    # ---------- Offline: Piper ----------
    def _piper(self, text: str) -> str:
        try:
            subprocess.run(
                ["piper", "--model", config.PIPER_MODEL, "--output_file", TMP_WAV],
                input=text.encode("utf-8"),
                check=True,
            )
            return TMP_WAV
        except Exception as e:
            print(f"[Voice] Και το Piper απέτυχε: {e} — δεν θα ακουστεί φωνή.")
            return ""
