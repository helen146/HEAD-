# -*- coding: utf-8 -*-
"""
prosopa.py — Αυτόματη φόρτωση χαρακτήρων για το Κεφάλι AI.

Κάθε χαρακτήρας είναι ΕΝΑ αρχείο .json μέσα στον φάκελο characters/.
Για να προσθέσεις νέο χαρακτήρα ΔΕΝ πειράζεις καθόλου τον κώδικα:
απλά αντιγράφεις το characters/_protypo.json, το μετονομάζεις
(π.χ. pythagoras.json) και συμπληρώνεις τα πεδία.
Δες οδηγίες στο README_PROSOPA.md.

Χρήση από το κυρίως πρόγραμμα:

    from modules.prosopa import fortose_prosopa
    FILOSOFOI = fortose_prosopa()

Το FILOSOFOI είναι λεξικό: κλειδί = το όνομα του json αρχείου
(π.χ. "aristotelis"), τιμή = λεξικό με name, intro, prompt,
voice_id, frasis_anamonis.

Το ίδιο κλειδί χρησιμοποιείται:
  - στο QR code (το κείμενο του QR είναι το κλειδί, π.χ. "pythagoras")
  - στα αρχεία ήχου αναμονής (audio_frasis/pythagoras_1.wav κ.λπ.)
"""

import json
import os
import sys

# Ο φάκελος characters/ βρίσκεται δίπλα στον φάκελο modules/
_RIZA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(_RIZA, "characters")

# Πεδία που ΠΡΕΠΕΙ να έχει κάθε χαρακτήρας
_YPOXREOTIKA = ("name", "intro", "prompt", "voice_id")


def _elegxos(kleidi, dedomena):
    """Ελέγχει ότι ο χαρακτήρας έχει όλα τα απαραίτητα πεδία.
    Επιστρέφει λίστα με τυχόν προβλήματα (κενή = όλα καλά)."""
    provlimata = []
    for pedio in _YPOXREOTIKA:
        timi = dedomena.get(pedio)
        if not isinstance(timi, str) or not timi.strip():
            provlimata.append(f"λείπει ή είναι κενό το πεδίο '{pedio}'")
    if not kleidi.isascii() or " " in kleidi:
        provlimata.append(
            "το όνομα αρχείου πρέπει να έχει μόνο λατινικούς "
            "χαρακτήρες χωρίς κενά (γίνεται κείμενο QR code)"
        )
    return provlimata


def fortose_prosopa(fakelos=None, ektiposi=True):
    """Διαβάζει όλα τα .json από τον φάκελο characters/ και
    επιστρέφει λεξικό με τους χαρακτήρες.

    Αρχεία που ξεκινούν με '_' (π.χ. _protypo.json) αγνοούνται,
    ώστε το πρότυπο να μη φορτώνεται ως χαρακτήρας.
    """
    fakelos = fakelos or CHARACTERS_DIR
    prosopa = {}

    if not os.path.isdir(fakelos):
        print(f"[Πρόσωπα] ΣΦΑΛΜΑ: δεν βρέθηκε ο φάκελος {fakelos}")
        sys.exit(1)

    for arxeio in sorted(os.listdir(fakelos)):
        if not arxeio.endswith(".json") or arxeio.startswith("_"):
            continue

        kleidi = arxeio[:-5]  # "aristotelis.json" -> "aristotelis"
        diadromi = os.path.join(fakelos, arxeio)

        try:
            with open(diadromi, encoding="utf-8") as f:
                dedomena = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[Πρόσωπα] ΣΦΑΛΜΑ στο {arxeio}: χαλασμένο JSON ({e})")
            print("           Ο χαρακτήρας ΔΕΝ φορτώθηκε. "
                  "Έλεγξε κόμματα και εισαγωγικά.")
            continue

        provlimata = _elegxos(kleidi, dedomena)
        if provlimata:
            print(f"[Πρόσωπα] ΣΦΑΛΜΑ στο {arxeio}:")
            for p in provlimata:
                print(f"           - {p}")
            print("           Ο χαρακτήρας ΔΕΝ φορτώθηκε.")
            continue

        # Προαιρετικό πεδίο: φράσεις αναμονής (λίστα κειμένων)
        dedomena.setdefault("frasis_anamonis", [])

        prosopa[kleidi] = dedomena

    if not prosopa:
        print("[Πρόσωπα] ΣΦΑΛΜΑ: δεν φορτώθηκε κανένας χαρακτήρας!")
        sys.exit(1)

    if ektiposi:
        onomata = ", ".join(p["name"] for p in prosopa.values())
        print(f"[Πρόσωπα] Φορτώθηκαν {len(prosopa)} χαρακτήρες: {onomata}")

    return prosopa


def lista_onomaton(prosopa):
    """Επιστρέφει τα ονόματα των χαρακτήρων ως ένα string,
    χρήσιμο για το initial_prompt του whisper στο ears.py,
    ώστε η αναγνώριση ομιλίας να πιάνει σωστά τα ονόματα."""
    return ", ".join(p["name"] for p in prosopa.values()) + ". "


if __name__ == "__main__":
    # Δοκιμή: python3 modules/prosopa.py
    p = fortose_prosopa()
    for kleidi, x in p.items():
        print(f"\n--- {kleidi} ---")
        print(f"  Όνομα: {x['name']}")
        print(f"  Intro: {x['intro']}")
        print(f"  Voice: {x['voice_id']}")
        print(f"  Φράσεις αναμονής: {len(x['frasis_anamonis'])}")
