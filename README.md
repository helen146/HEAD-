# Kefali AI

Kefali AI ("kefali" is Greek for "head") is a 3D-printed animatronic head that lets children talk with AI personas of Aristotle, Archimedes and Theano, in Greek. I built it for my students on Pserimos, a small island in the South Aegean, as a museum that travels to the classroom. The head is Gaël Langevin's open-source [InMoov](https://inmoov.fr) design, printed at original scale with my own adaptations. This repository is the software that makes it listen, think, speak and move its jaw and eyes.

## How it works

A child holds a QR card up to the camera, the persona introduces itself, and from then on the child just talks. Each answer goes through five stations:

| | Station | File | What happens |
|---|---|---|---|
| 1 | The card | `modules/qr_listener.py` | A background thread reads QR cards from the webcam (OpenCV + pyzbar). The card's text is the persona's file name, e.g. `aristotelis`. |
| 2 | Listening | `modules/ears.py` | RMS voice-activity detection on the separate AB13X USB microphone: recording starts after two voice frames, keeps the 0.3 s before them, and stops after 1.2 s of silence. ElevenLabs Scribe v2 transcribes Greek speech; local faster-whisper (`small`) is the fallback. |
| 3 | Thinking | `modules/brain.py` | The question and the persona's prompt go to the Claude API (`claude-haiku-5-5`, the fastest current model). Each persona answers in at most 5 short sentences, direct answer first. A pre-recorded "thinking" phrase fills the wait. |
| 4 | Speaking | `modules/voice.py` | ElevenLabs (`eleven_flash_v2_5`) gives each persona its own voice; the answer's voice is made while the thinking phrase is still playing. If the cloud voice fails, Piper speaks locally. |
| 5 | Jaw and eyes | `modules/xrp_link.py`, `modules/eye_motion.py`, `xrp/main.py` | While speech plays, the Pi sends jaw loudness every 50 ms and triggers an eye glance. Small random glances also happen while listening. The head servo is not commanded. |

The jaw follows the loudness of the voice (amplitude-envelope jaw sync); it is not phoneme-level lip-sync.

After every answer the log shows how long each stage took, e.g. `⏱ αναγνώριση 1.5 s · Claude 2.1 s · φωνή 1.0 s · αναμονή 3.9 s` (recognition, Claude, voice, total wait). Watch it with `journalctl -u kefali.service -f`.

## Hardware

| Part | Role |
|---|---|
| Raspberry Pi 4, 2 GB | The brain: runs everything in this repo except `xrp/` |
| XRP controller (MicroPython) | The body: drives the four servos below |
| Servo, XRP port 1 | Head rotation; currently disconnected and never commanded by the app |
| HK15298 servo, XRP port 2 | Jaw |
| USB webcam | QR cards (video) |
| AB13X USB microphone | Questions in Greek (ALSA card `Audio`) |
| Turbo-X SP-110 speaker, mounted in a 3D-printed ear | Voice, from the Pi's 3.5 mm jack (ALSA card `Headphones`) |
| Two micro servos, XRP ports 3 and 4 | Servo 3 glances left/right around 60° and Servo 4 glances up/down around 50° while listening and speaking; the head servo stays still |

## Repository layout

```
kefali_ai.py          main loop: card → introduction → listen → think → speak
config.py             every setting in one place; loads the API keys
characters/           one JSON file per persona (+ _protypo.json template)
modules/
  prosopa.py          loads the personas from characters/
  qr_listener.py      reads QR cards on a background thread
  ears.py             voice-activity detection + Scribe v2 / faster-whisper
  brain.py            Claude API; cleans answers for speech
  voice.py            ElevenLabs, with Piper as fallback
  xrp_link.py         loudness envelope; sends jaw frames in time with playback
  eye_motion.py       random calibrated eye glances and a glance at speech start
  connectivity.py     checks the internet before each answer
xrp/main.py           MicroPython that runs on the XRP
set_eyes.py           set fixed eye angles while Kefali is stopped
ftiaxe_frasis.py      generates the "thinking" phrases (run once)
deploy/               systemd service and ALSA config for the Pi
README_PROSOPA.md     how to add a persona (in Greek)
```

## Pi ↔ XRP protocol

Plain text over USB serial (115200 baud), one command per line:

| Command | Meaning |
|---|---|
| `J:<0-255>` | Jaw loudness for this 50 ms frame (0 = closed). The XRP maps it to 15–50° and smooths it. |
| `S:<port>:<degrees>` | Move any servo, e.g. `S:3:60` (eyes to centre) |
| `PING` | The XRP answers `PONG` |

The XRP limits Servo 2 to 15–50°, Servo 3 to 30–90°, and Servo 4 to 30–60°. To set fixed eye positions while Kefali is stopped, run `./bin/python3 set_eyes.py --horizontal 60 --vertical 50` on the Pi.

## Setup

### Raspberry Pi (Raspberry Pi OS 64-bit)

```bash
sudo apt update
sudo apt install -y ffmpeg alsa-utils libzbar0 python3-opencv
git clone https://github.com/helen146/HEAD-.git ~/kefali-ai
cd ~/kefali-ai
python3 -m venv --system-site-packages .
./bin/pip install -r requirements.txt
```

1. **API keys:** copy `kleidia.example.txt` to `kleidia.txt` and add your Anthropic and ElevenLabs keys. `kleidia.txt` is in `.gitignore`; never commit it.
2. **Offline voice:** put the Piper binary and the `el_GR-rapunzelina-low` voice in `~/piper/`.
3. **Audio:** `cp deploy/asoundrc.example ~/.asoundrc`. The microphone is set by card name in `config.py` (`MIC_DEVICE`); `arecord -l` lists the names. On the tested Pi, copy `deploy/volume.conf` to `/etc/systemd/system/kefali.service.d/volume.conf` and reload systemd to set the jack output to maximum at each start.
4. **Thinking phrases:** `./bin/python3 ftiaxe_frasis.py` (once, and again after adding a persona).
5. **Run:** `./bin/python3 kefali_ai.py`
6. **Start on boot:** edit `deploy/kefali.service` (replace `YOUR_USER`), then follow the steps at the top of that file.

### XRP

Save `xrp/main.py` to the XRP as `main.py` (with Thonny or mpremote); it runs on every boot. Close Thonny before starting the Pi program, because two programs cannot share the serial port. Power the servos from the XRP's batteries, not USB alone. Servo commands are clamped to the tested ranges for this mechanism; check the physical motion when adapting the project to another head.

## Adding a persona

Copy `characters/_protypo.json` to a new file (e.g. `pythagoras.json`), fill in the name, introduction, ElevenLabs voice, prompt and thinking phrases, and print a QR code whose text is the file name (`pythagoras`). No code changes. Full guide, in Greek: [README_PROSOPA.md](README_PROSOPA.md).

## Speed settings

All in `config.py`:

| Setting | Now | Trade-off |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Fastest. `claude-sonnet-4-6` (the previous model) may give richer answers but is slower. |
| `STT_PROVIDER` | `elevenlabs` | Scribe v2 needs internet; local Whisper is used when it fails. |
| `WHISPER_SIZE` | `small` | Local fallback has better Greek recognition but is slow on the Pi. |
| `WHISPER_BEAM_SIZE` | `1` | `5` is more careful in Greek but slower. |
| `SILENCE_STOP_SEC` | `1.2` | Lower ends recording sooner, but may cut off a child who pauses. |
| Sentence limit | 5 | Set in each `characters/*.json` prompt; longer answers take longer to write and to voice. |

## Status and limitations

- **Greek only today.** The speech recognition is told to expect Greek and every persona answers in Greek. English is in progress.
- **Dialogue needs the internet.** Without it, the head still listens and transcribes, then answers with one fixed line in Piper's voice.
- **The cloud-voice timeout is 60 s,** far too long for a child to wait. Shortening it is next.
- **No local language model yet.** `brain.py` still has an Ollama path from the original plan; it has never run on the Pi 4, whose 2 GB of RAM it would fill. Running a Greek-capable open-weight model on hardware beside the head is my next research step.

## Credits

- Head: [InMoov](https://inmoov.fr) by Gaël Langevin
- XRP controller: SparkFun; platform by DEKA and WPI
- Libraries and services: faster-whisper, Anthropic Claude API, ElevenLabs, Piper, OpenCV, pyzbar
- Advisor: Dr Anastasios Kollias · Workshop and printers: MellonLab, Piraeus

I used Claude (Anthropic) as a programming assistant: debugging the audio pipeline and the voice-activity detection, sorting out ALSA device naming and the systemd service, and drafting portions of the Python code. I designed the architecture, wired and assembled the hardware, and tested, adapted and integrated the code on the device.
