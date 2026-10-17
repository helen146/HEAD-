# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/brain.py
Ο «εγκέφαλος»: παίρνει την ερώτηση του μαθητή + το system prompt του
φιλοσόφου και επιστρέφει την απάντηση σε χαρακτήρα.

Δύο μηχανές πίσω από την ΙΔΙΑ συνάρτηση think():
  • Online  → Anthropic API (claude)
  • Offline → Ollama (τοπικό μοντέλο στο Pi)
"""

import json
import re
import urllib.request

import config


ASR_TRANSCRIPT_GUIDANCE = (
    "Το μήνυμα του μαθητή προέρχεται από τοπική αναγνώριση ομιλίας. "
    "Αν ένα όνομα ή μία φράση έχει σαφή φωνητική αντιστοιχία στα συμφραζόμενα, "
    "πες σύντομα τι κατάλαβες και απάντησε. Αν δεν είναι σαφές, ζήτησε επανάληψη. "
    "Μην επινοείς άγνωστα πρόσωπα."
)


def clean_for_speech(text: str) -> str:
    """Καθαρίζει σύμβολα markdown (**, ##, - κ.λπ.) — αλλιώς το TTS τα προφέρει!"""
    text = re.sub(r"[*_`#]+", "", text)          # έμφαση, κεφαλίδες, κώδικας
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)   # κουκκίδες λίστας
    text = re.sub(r"\n{2,}", "\n", text)         # πολλαπλές κενές γραμμές
    return text.strip()


class Brain:
    def __init__(self):
        self._anthropic = None  # φορτώνεται μόνο αν χρειαστεί

    def warmup(self):
        """Φορτώνει τη βιβλιοθήκη του Claude ΤΩΡΑ, ώστε η πρώτη ερώτηση
        μπροστά στα παιδιά να μην περιμένει το import."""
        if self._anthropic is None and config.ANTHROPIC_API_KEY:
            try:
                from anthropic import Anthropic
                self._anthropic = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            except Exception as e:
                print(f"[Brain] Δεν φόρτωσε ο Claude ({e}) — θα ξαναδοκιμάσω στην ερώτηση.")

    # ---------- Δημόσια συνάρτηση ----------
    def think(self, system_prompt: str, history: list, question: str, online: bool) -> str:
        """
        history: λίστα από dicts {"role": "user"/"assistant", "content": "..."}
        Επιστρέφει το κείμενο της απάντησης.
        """
        messages = history + [{"role": "user", "content": question}]
        if config.PHASE >= 2:
            system_prompt += "\n\n" + ASR_TRANSCRIPT_GUIDANCE
        if online and config.ANTHROPIC_API_KEY:
            try:
                return clean_for_speech(self._think_anthropic(system_prompt, messages))
            except Exception as e:
                print(f"[Brain] Το Anthropic API απέτυχε ({e}) → δοκιμάζω Ollama…")
        return clean_for_speech(self._think_ollama(system_prompt, messages))

    # ---------- Online: Anthropic ----------
    def _think_anthropic(self, system_prompt: str, messages: list) -> str:
        if self._anthropic is None:
            from anthropic import Anthropic
            self._anthropic = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = self._anthropic.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=600,   # αρκετό για 5 σύντομες ελληνικές προτάσεις
            thinking={"type": "disabled"},  # Haiku 5.5: γρήγορη ομιλία χωρίς σκέψη
            system=system_prompt,
            messages=messages,
        )
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("Η απάντηση του Claude κόπηκε στο όριο tokens")
        text = " ".join(
            block.text for block in resp.content
            if block.type == "text" and block.text
        ).strip()
        if not text:
            raise RuntimeError("Ο Claude δεν επέστρεψε κείμενο")
        return text

    # ---------- Offline: Ollama ----------
    def _think_ollama(self, system_prompt: str, messages: list) -> str:
        payload = {
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
        }
        req = urllib.request.Request(
            config.OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["message"]["content"].strip()
        except Exception as e:
            print(f"[Brain] Και το Ollama απέτυχε: {e}")
            return "Συγγνώμη, ο νους μου θόλωσε για μια στιγμή. Ρώτησέ με ξανά."
