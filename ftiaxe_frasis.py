#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ftiaxe_frasis.py — Παράγει τις έτοιμες φράσεις αναμονής με ElevenLabs.

Διαβάζει τις frasis_anamonis από τα αρχεία characters/*.json,
οπότε νέος χαρακτήρας = αυτόματα και οι δικές του φράσεις.
Τρέχει ΜΙΑ φορά (και ξανά μόνο όταν προστεθεί χαρακτήρας ή
αλλάξουν οι φράσεις). Παραλείπει όσα αρχεία υπάρχουν ήδη.

Χρήση:  python3 ftiaxe_frasis.py
"""

import os
import requests

import config  # API key, μοντέλο φωνής και φάκελος φράσεων
from modules.prosopa import fortose_prosopa

OUT_DIR = config.FRASIS_DIR


def tts(text, voice_id, out_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = requests.post(
        url,
        headers={"xi-api-key": config.ELEVENLABS_API_KEY},
        json={"text": text, "model_id": config.ELEVEN_MODEL},
        timeout=60,
    )
    r.raise_for_status()
    mp3_tmp = out_path + ".mp3"
    with open(mp3_tmp, "wb") as f:
        f.write(r.content)
    # μετατροπή σε wav για αναπαραγωγή χωρίς καθυστέρηση με aplay
    os.system(f'ffmpeg -y -loglevel error -i "{mp3_tmp}" -ar 48000 -ac 2 "{out_path}"')
    os.remove(mp3_tmp)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    prosopa = fortose_prosopa()

    for kleidi, xaraktiras in prosopa.items():
        frasis = xaraktiras.get("frasis_anamonis", [])
        if not frasis:
            print(f"[{kleidi}] Δεν έχει φράσεις αναμονής — παραλείπεται.")
            continue
        for i, frasi in enumerate(frasis, 1):
            out = os.path.join(OUT_DIR, f"{kleidi}_{i}.wav")
            if os.path.exists(out):
                print(f"Υπάρχει ήδη: {out} — παραλείπεται.")
                continue
            print(f"Παράγω: {out}  ({frasi})")
            tts(frasi, xaraktiras["voice_id"], out)

    print("Έτοιμο! Οι φράσεις είναι στο", OUT_DIR)


if __name__ == "__main__":
    main()
