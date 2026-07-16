#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Κεφάλι AI — kefali_ai.py  (κύριο πρόγραμμα)

ΦΑΣΗ 2 (μικρόφωνο) — η φυσική ροή:
    Η κάμερα σαρώνει συνεχώς για QR
    → μαθητής δείχνει QR → ο φιλόσοφος ΣΥΣΤΗΝΕΤΑΙ με τη φωνή του
    → ανοίγει το μικρόφωνο → ο μαθητής ρωτά
    → Claude σκέφτεται → ElevenLabs μιλά → η σιαγόνα κουνιέται στο XRP
    → ξανά μικρόφωνο (συνεχίζεται η κουβέντα με τον ίδιο φιλόσοφο)
    → νέο QR οποιαδήποτε στιγμή → αλλάζει φιλόσοφος

ΦΑΣΗ 1 (PHASE = 1 στο config): ίδια ροή, αλλά η ερώτηση γράφεται στο
πληκτρολόγιο αντί να ειπωθεί.

Έξοδος: Ctrl+C
"""

import sys
import time

import config
from modules.brain import Brain
from modules.connectivity import is_online
from modules.ears import Ears
from modules.qr_listener import QRListener
from modules.voice import Voice
from modules.xrp_link import XRPLink, play_with_jaw
import dotenv

PERSONA_KEYS = list(config.PERSONAS.keys())


def main():
    dotenv.load_dotenv()
    print("═" * 50)
    print("  ΚΕΦΑΛΙ AI — Mellon Lab, Πειραιάς")
    print("═" * 50)

    brain, voice, ears = Brain(), Voice(), Ears()
    xrp = XRPLink()
    qr = QRListener()
    qr.start()

    online = is_online()
    print(f"Λειτουργία: {'ONLINE (Claude + ElevenLabs)' if online else 'OFFLINE'}")

    # Φορτώνουμε το μοντέλο ομιλίας ΤΩΡΑ, όχι μπροστά στα παιδιά
    ears.warmup()

    persona_id = config.DEFAULT_PERSONA
    history = []

    def speak(text, persona):
        """Λέει κάτι φωναχτά και κουνά τη σιαγόνα."""
        wav = voice.speak_to_wav(text, persona["eleven_voice_id"], is_online())
        play_with_jaw(wav, xrp)

    def switch_persona(pid, introduce=True):
        """Αλλάζει φιλόσοφο και τον βάζει να συστηθεί."""
        nonlocal persona_id, history
        persona_id = pid
        history = []  # νέος φιλόσοφος → καθαρή κουβέντα
        p = config.PERSONAS[pid]
        print(f"\n🎭 Ενεργός φιλόσοφος: {p['name']}")
        if introduce:
            intro = p.get("intro", f"Γεια σας. Είμαι ο {p['name']}. Ρωτήστε με ό,τι θέλετε.")
            print(f"🗣️  {p['name']}: {intro}")
            speak(intro, p)

    print(f"\n🎭 Ενεργός φιλόσοφος: {config.PERSONAS[persona_id]['name']}")
    print("   (Δείξε ένα QR code στην κάμερα για να αλλάξεις φιλόσοφο)\n")

    try:
        while True:
            # 1) Σκαναρίστηκε νέο QR; → αλλαγή φιλοσόφου + σύσταση
            scanned = qr.get_scanned()
            if scanned and scanned != persona_id:
                switch_persona(scanned)
            elif scanned:
                # ίδιο QR ξανά → απλώς ξανασυστήνεται
                switch_persona(scanned)

            persona = config.PERSONAS[persona_id]

            # 2) Ερώτηση μαθητή (η ακρόαση διακόπτεται αν σκαναριστεί QR)
            question = ears.listen(qr)

            # Κενή ερώτηση: στη Φάση 2 συνεχίζουμε (μπορεί να μη μίλησε κανείς),
            # στη Φάση 1 σημαίνει έξοδο.
            if not question:
                if config.PHASE >= 2:
                    time.sleep(0.3)
                    continue
                print("Αντίο! 👋")
                break

            # Εντολές πληκτρολογίου: !1 !2 !3 → αλλαγή φιλοσόφου χωρίς QR
            if question.startswith("!") and question[1:].isdigit():
                idx = int(question[1:]) - 1
                if 0 <= idx < len(PERSONA_KEYS):
                    switch_persona(PERSONA_KEYS[idx])
                continue

            # 3) Σκέψη
            online = is_online()
            print("💭 Ο φιλόσοφος σκέφτεται…")
            answer = brain.think(persona["system_prompt"], history, question, online)
            print(f"\n🗣️  {persona['name']}: {answer}\n")

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            history[:] = history[-2 * config.HISTORY_MAX_TURNS :]

            # 4) Φωνή + σιαγόνα
            speak(answer, persona)

    except KeyboardInterrupt:
        print("\nΑντίο! 👋")
    finally:
        xrp.close()
        qr.close()


if __name__ == "__main__":
    sys.exit(main())
