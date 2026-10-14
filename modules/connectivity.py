# -*- coding: utf-8 -*-
"""
Κεφάλι AI — modules/connectivity.py
Ελέγχει αν υπάρχει πρόσβαση στο internet (και στο Anthropic API).
Αυτό αποφασίζει ποια «μηχανή» θα τρέξει σε κάθε στάδιο (online ή offline).
"""

import socket


def is_online(timeout: float = 3.0) -> bool:
    """Γρήγορος έλεγχος: μπορούμε να ανοίξουμε TCP σύνδεση στο api.anthropic.com;"""
    try:
        sock = socket.create_connection(("api.anthropic.com", 443), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False
