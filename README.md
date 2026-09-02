# Kefali AI — Software Package (Pi = brain, XRP = motion)

New architecture:
- **Raspberry Pi 4 = brain**: QR, question, Claude, voice, speaker
- **XRP = motion controller**: jaw HK15298 (servo port 1) + other servos
- Pi ↔ XRP connection: **USB-C cable** (serial) — simple and instant
- No LEDs — the eyes are autonomous modules that connect to nothing

---

## Structure

```
kefali-ai/
├── kefali_ai.py            ← MAIN program (Phase 1 & 2)
├── config.py               ← ALL settings (pins, personas, voices, keys)
├── kleidia.txt             ← (YOU create this — see below, do NOT share it)
├── modules/
│   ├── connectivity.py     ← internet check (online/offline)
│   ├── brain.py            ← brain: Claude (online) / Ollama (offline)
│   ├── voice.py            ← voice: ElevenLabs (online) / Piper (offline)
│   ├── ears.py             ← question: keyboard (P1) / microphone+Whisper (P2)
│   ├── xrp_link.py         ← bridge to the XRP: motion commands + sync
│   └── qr_listener.py      ← listens to the ESP32-CAM on serial
├── esp32cam/
│   └── kefali_qr_scanner.ino  ← sketch for the ESP32-CAM (QR scanner)
└── xrp/
    └── main.py             ← MicroPython for the XRP (receives commands, drives servo)
```

---

## 1. The API key — WHAT YOU MUST DO (once)

The key you created at console.anthropic.com for Colab is the SAME one
you'll use here — but I can't enter it; it's stored only in your Colab
Secrets. Do one of the two:

**Option A (simplest):** create a file `kleidia.txt` inside the
`kefali-ai` folder, with the contents:

```
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY
ELEVENLABS_API_KEY=YOUR-ELEVENLABS-KEY   (optional)
```

The program reads it automatically. ⚠️ Don't upload/send it anywhere.

**Option B:** environment variables in the terminal:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export ELEVENLABS_API_KEY="..."
```

If you've lost the key: console.anthropic.com → API Keys → create a
new one (the old one is never shown in full again).

## 2. Installation on the Raspberry Pi 3 B+

```bash
sudo apt update
sudo apt install -y ffmpeg alsa-utils

# On Raspberry Pi OS (Bookworm), pip needs the extra flag:
pip install anthropic pyserial --break-system-packages
# For Phase 2 (microphone):
pip install faster-whisper --break-system-packages
# For offline voice (optional):
#   Piper: download the binary + the el_GR-rapunzelina-low model
#          and set the path in config.py (PIPER_MODEL)
```

⚠️ **Honest note about the Pi 3 B+ (1GB RAM):** the online mode
(Claude + ElevenLabs) works just fine — it's simply network calls.
**Ollama, however, does NOT fit** in 1GB RAM, so there is no offline
brain on this board: **the head needs internet** in order to answer.
Piper (offline voice) works but slowly, and faster-whisper only with the
"tiny" model. If a Pi 5 turns up later, all the offline features unlock
with no code changes.

## 3. Settings before the first run (`config.py`)

- `PHASE = 1` (keyboard) or `2` (microphone)
- `eleven_voice_id` for each philosopher (from the ElevenLabs Voice Library)
- **Jaw:** set `JAW_CLOSED_DEG` / `JAW_OPEN_DEG` with careful testing —
  wrong limits strain the mechanism. Range 0°–20° per InMoov.
  (Same values also at the top of `xrp/main.py`.)

## 4. Wiring

| What | Where |
|---|---|
| Jaw HK15298 | **XRP servo port 1** |
| Other servos (future) | XRP servo ports 2, 3, 4 |
| XRP ↔ Pi | USB-C cable → shows up as `/dev/ttyACM0` |
| Servo power | From the **XRP battery** — not USB alone! The HK15298 draws a fair bit of current. |
| Speaker | On the Pi's audio output (3.5mm/USB/HDMI — whatever you have) |
| ESP32-CAM | USB → `/dev/ttyUSB0` |

**Nothing** connects to the Pi's GPIO anymore. The autonomous eye modules
connect to nothing — they go in as-is. The online/offline status shows on
the terminal screen.

### Installation on the XRP (once)

1. Open Thonny, connect the XRP
2. Save `xrp/main.py` to the XRP **as `main.py`** → runs automatically
   on every boot
3. **Close Thonny** before running the program on the Pi — two programs
   can't hold the same serial port
4. Connection test from the Pi: `kefali_ai.py` prints
   "[XRP] Connected…" if everything is fine

## 5. Running

```bash
python3 kefali_ai.py
```

- Scanning a QR from the ESP32-CAM → switches philosopher automatically
- `!1` / `!2` → switch philosopher from the keyboard (if the ESP32 is missing)
- Empty Enter → exit
- Also runs on a laptop **with no hardware** (simulation mode) —
  ideal for testing the "brain" first.

## 6. ESP32-CAM (QR scanner)

1. Arduino IDE → ESP32 core **3.2.1** (not 3.3.0)
2. Library **ESP32QRCodeReader** — the fixed fork (Random Nerd Tutorials)
3. Tools: Board = AI Thinker ESP32-CAM, Partition = Huge APP, PSRAM = Enabled
4. Upload `esp32cam/kefali_qr_scanner.ino`
5. Make QR codes with the contents **exactly** `aristotelis` and `arximidis`

## 7. How jaw sync works

The audio plays on the Pi's speaker. The Pi splits the voice into 50 ms
frames, measures the loudness of each frame, and sends the XRP one
`J:<0-255>` command per frame. The XRP simply converts the loudness into
a 0°–20° angle (with a bit of "smoothing" for fluid motion). This way the
"heavy" part stays on the Pi and the XRP does only what suits it: motion.

For future servos (arms, neck, etc.) there's already a ready command:
on the Pi, `xrp.set_servo(2, 45)` → the servo on port 2 goes to 45°.

## 8. What's left to you

- The `kleidia.txt` with your key (step 1)
- ElevenLabs voice IDs in `config.py`
- Setting the jaw limits in `config.py` AND in `xrp/main.py` (dry-fit first!)
- Battery on the XRP once the HK15298 is plugged in
