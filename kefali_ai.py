#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Κεφάλι AI — kefali_ai.py  (κύριο πρόγραμμα)

ΦΑΣΗ 2 (μικρόφωνο) — η φυσική ροή:
    Η κάμερα σαρώνει συνεχώς για QR
    → μαθητής δείχνει QR → ο φιλόσοφος ΣΥΣΤΗΝΕΤΑΙ με τη φωνή του
    → ανοίγει το μικρόφωνο → ο μαθητής ρωτά
    → φράση αναμονής («Χμμμ…») όσο σκέφτεται ο Claude
    → ElevenLabs μιλά → η σιαγόνα κουνιέται στο XRP
    → ξανά μικρόφωνο (συνεχίζεται η κουβέντα με τον ίδιο φιλόσοφο)
    → νέο QR οποιαδήποτε στιγμή → αλλάζει φιλόσοφος

Οι φιλόσοφοι φορτώνονται από τα αρχεία characters/*.json
(modules/prosopa.py) — νέος φιλόσοφος = νέο αρχείο, όχι νέος κώδικας.

ΦΑΣΗ 1 (PHASE = 1 στο config): ίδια ροή, αλλά η ερώτηση γράφεται στο
πληκτρολόγιο αντί να ειπωθεί (μόνο για δοκιμές).

Έξοδος: Ctrl+C
"""

import glob
import os
import random
import sys
import threading
import time

import config
from modules.brain import Brain
from modules.connectivity import is_online
from modules.ears import Ears
from modules.prosopa import fortose_prosopa, lista_onomaton
from modules.qr_listener import QRListener
from modules.voice import Voice
from modules.xrp_link import XRPLink, play_with_jaw


def main():
    print("═" * 50)
    print("  ΚΕΦΑΛΙ AI — MellonLab, Πειραιάς")
    print("═" * 50)

    personas = fortose_prosopa()
    persona_keys = list(personas.keys())

    brain, voice = Brain(), Voice()
    ears = Ears(names_hint=lista_onomaton(personas))
    xrp = XRPLink()
    qr = QRListener(personas)
    qr.start()

    online = is_online()
    print(f"Λειτουργία: {'ONLINE (Claude + ElevenLabs)' if online else 'OFFLINE'}")

    # Φορτώνουμε το μοντέλο ομιλίας και τον Claude ΤΩΡΑ, όχι μπροστά στα παιδιά
    ears.warmup()
    brain.warmup()
    # Μετράμε τον θόρυβο του δωματίου ΠΡΙΝ μιλήσει ο φιλόσοφος, και
    # ρυθμίζουμε ανάλογα το πόσο σιγανή φωνή «ακούει» το κεφάλι
    ears.calibrate()

    persona_id = config.DEFAULT_PERSONA if config.DEFAULT_PERSONA in personas else persona_keys[0]
    history = []

    def speak(text, persona):
        """Λέει κάτι φωναχτά και κουνά τη σιαγόνα."""
        wav = voice.speak_to_wav(text, persona["voice_id"], is_online())
        play_with_jaw(wav, xrp)

    def start_thinking_phrase(pid):
        """Παίζει μια έτοιμη φράση αναμονής ΠΑΡΑΛΛΗΛΑ με την κλήση στον
        Claude, με κίνηση σιαγόνας. Επιστρέφει το νήμα, ή None αν δεν
        υπάρχουν φράσεις (π.χ. δεν έχει τρέξει ακόμα το ftiaxe_frasis.py)."""
        files = glob.glob(os.path.join(config.FRASIS_DIR, f"{pid}_*.wav"))
        if not files:
            return None
        t = threading.Thread(
            target=play_with_jaw, args=(random.choice(files), xrp), daemon=True
        )
        t.start()
        return t

    def switch_persona(pid, introduce=True):
        """Αλλάζει φιλόσοφο και τον βάζει να συστηθεί."""
        nonlocal persona_id, history
        persona_id = pid
        history = []  # νέος φιλόσοφος → καθαρή κουβέντα
        p = personas[pid]
        print(f"\n🎭 Ενεργός φιλόσοφος: {p['name']}")
        if introduce:
            print(f"🗣️  {p['name']}: {p['intro']}")
            speak(p["intro"], p)

    print(f"\n🎭 Ενεργός φιλόσοφος: {personas[persona_id]['name']}")
    print("   (Δείξε ένα QR code στην κάμερα για να αλλάξεις φιλόσοφο)\n")

    try:
        while True:
            # 1) Σκαναρίστηκε QR; → αλλαγή φιλοσόφου + σύσταση
            #    (το ίδιο QR ξανά → απλώς ξανασυστήνεται)
            scanned = qr.get_scanned()
            if scanned:
                switch_persona(scanned)

            persona = personas[persona_id]

            # 2) Ερώτηση μαθητή (η ακρόαση διακόπτεται αν σκαναριστεί QR)
            question = ears.listen(qr)
            t_question = time.monotonic()   # μόλις τελείωσε η αναγνώριση

            # Κενή ερώτηση: στη Φάση 2 συνεχίζουμε (μπορεί να μη μίλησε κανείς),
            # στη Φάση 1 σημαίνει έξοδο.
            if not question:
                if config.PHASE >= 2:
                    time.sleep(0.3)
                    continue
                print("Αντίο! 👋")
                break

            # Φάση 1 μόνο: !1 !2 !3 → αλλαγή φιλοσόφου από το πληκτρολόγιο
            if question.startswith("!") and question[1:].isdigit():
                idx = int(question[1:]) - 1
                if 0 <= idx < len(persona_keys):
                    switch_persona(persona_keys[idx])
                continue

            # 3) Σκέψη — η φράση αναμονής γεμίζει τη σιωπή όσο περιμένουμε
            print("💭 Ο φιλόσοφος σκέφτεται…")
            filler = start_thinking_phrase(persona_id)
            online = is_online()      # ένας έλεγχος ανά ερώτηση, όχι δύο
            t_think = time.monotonic()
            answer = brain.think(persona["prompt"], history, question, online)
            think_sec = time.monotonic() - t_think
            print(f"\n🗣️  {persona['name']}: {answer}\n")

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            history[:] = history[-2 * config.HISTORY_MAX_TURNS :]

            # 4) Φωνή + σιαγόνα. Η φωνή της απάντησης φτιάχνεται ΟΣΟ ακόμα
            #    παίζει η φράση αναμονής· μετά περιμένουμε να τελειώσει η
            #    φράση, ώστε να μη μιλάνε δύο φωνές μαζί.
            t_voice = time.monotonic()
            wav = voice.speak_to_wav(answer, persona["voice_id"], online)
            voice_sec = time.monotonic() - t_voice
            if filler:
                filler.join()
            stt = ears.last_stt_sec or 0.0
            wait_sec = stt + (time.monotonic() - t_question)
            print(
                f"⏱  αναγνώριση {stt:.1f} s · Claude {think_sec:.1f} s · "
                f"φωνή {voice_sec:.1f} s · αναμονή ως την απάντηση {wait_sec:.1f} s"
            )
            play_with_jaw(wav, xrp)

    except KeyboardInterrupt:
        print("\nΑντίο! 👋")
    finally:
        xrp.close()
        qr.close()


if __name__ == "__main__":
    sys.exit(main())
