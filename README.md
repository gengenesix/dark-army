# ⚡ Dark-Army — Real-Time Face Swap + Voice Changer

**Swap your face AND change your voice in real-time during any video call.**
Works with Discord, Zoom, Google Meet, Teams, and OBS.

Created by **Zero** · v1.0.0

---

## 📥 Download & Install

### → [Download Latest Release](https://github.com/gengenesix/dark-army/releases/latest)

| Platform | File | How to Install |
|---|---|---|
| 🪟 **Windows** | `DarkArmy-Setup.exe` | Double-click → Next → Finish |
| 🐧 **Linux (any distro)** | `DarkArmy-x86_64.AppImage` | `chmod +x DarkArmy-x86_64.AppImage` then double-click |
| 🐧 **Ubuntu / Debian** | `darkarmy_1.0.0_amd64.deb` | `sudo dpkg -i darkarmy_1.0.0_amd64.deb` |

---

## 🎭 Features

- 👤 **Real-time face swap** — GPU-accelerated, <50ms latency
- 🎤 **Real-time voice changer** — RVC models, male↔female, any voice
- ⚡ Under 400ms end-to-end voice latency on GPU
- 🖥️ Works with **Discord, Zoom, Google Meet, Teams, OBS**
- 🎛️ One-click pitch presets (♀ Female, ♂ Deep Male, and more)
- 🔄 Switch voice models on-the-fly without restarting
- 💾 All settings saved persistently
- 🌐 Cross-platform: Windows, Linux, Ubuntu, Debian

---

## 🎤 Voice Changer Setup

### Windows
1. Install **VB-Cable** (free): https://vb-audio.com/Cable/
2. In Dark-Army Voice tab → set Output to **CABLE Input (VB-Audio)**
3. In Zoom/Discord → set Microphone to **CABLE Output (VB-Audio)**

### Linux
```bash
sudo apt install v4l2loopback-dkms   # for virtual camera
# For virtual mic, use PulseAudio virtual sink:
pactl load-module module-null-sink sink_name=darkarmy_mic
```

---

## 🪟 Windows Install Notes

The installer automatically:
- Installs Visual C++ 2015-2022 Runtime (required)
- Creates Start Menu + Desktop shortcuts
- Handles upgrades cleanly (kills old version first)

---

## 🐧 Linux Install Notes

```bash
# AppImage — works on any distro
chmod +x DarkArmy-x86_64.AppImage
./DarkArmy-x86_64.AppImage

# .deb — Ubuntu/Debian
sudo dpkg -i darkarmy_1.0.0_amd64.deb
darkarmy
```

---

## ⚙️ System Requirements

| | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | Intel i5 / AMD Ryzen 5 | i7 / Ryzen 7 |
| GPU | Not required | NVIDIA (CUDA) for best latency |
| Webcam | Required | HD 1080p |

---

## 🔧 Development

Built on top of [Echelon](https://github.com/gengenesix/echelon) face swap engine.
Voice changer powered by [w-okada/voice-changer](https://github.com/w-okada/voice-changer).

```
dark-army/
├── main.py                         # Entry point
├── ui/
│   ├── main_window.py              # Main window (tabbed: Face + Voice)
│   ├── voice_panel.py              # Voice changer UI panel
│   └── ...                         # All Echelon UI (unchanged)
├── core/
│   ├── voice_changer/
│   │   ├── vc_server.py            # w-okada server manager
│   │   ├── audio_pipeline.py       # Mic → VC server → output
│   │   └── model_manager.py        # RVC model download/load
│   └── ...                         # All Echelon core (unchanged)
└── .github/workflows/build.yml     # CI/CD — Windows + Linux
```

---

*Built with ❤️ by Zero*
