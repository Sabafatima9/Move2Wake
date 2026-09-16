<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:EF4444,100:F59E0B&height=220&section=header&text=Move2Wake%20%20%F0%9F%92%83&fontSize=45&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=The%20alarm%20that%20won't%20stop%20until%20you%20dance%20%7C%20MediaPipe%20%7C%20OpenCV%20%7C%20Tkinter&descAlignY=55&descSize=18" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=2500&pause=500&color=EF4444&center=true&vCenter=true&width=700&lines=%F0%9F%92%A4+Alarm+Rings+Until+You+Dance+for+10+Seconds!;%F0%9F%A6%B4+Real-Time+Body+Tracking+with+MediaPipe+Pose;%F0%9F%95%90+Set+Alarms+from+a+Tkinter+Dashboard;%F0%9F%9B%8C%EF%B8%8F+No+Button+Can+Snooze+This+-%20Only+Movement" alt="Typing SVG" />

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/Pose-MediaPipe-0097A9?style=for-the-badge&logoColor=white)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF4B4B?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)

</div>

---

## 🎯 Overview

**Move2Wake** is a desktop alarm application with a twist — **the alarm keeps ringing until you physically get up and dance in front of your webcam for 10 continuous seconds**. There is no snooze button you can reach half-asleep: the camera tracks your body with MediaPipe Pose, measures real movement, and only silences the ringing once your dance meter is full. It ships with both a **CLI version** (quick one-shot alarms) and a **Tkinter dashboard** (manage multiple saved alarms).

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### ⏰ Alarm Core
- 🔔 Loud beeping alarm loop (background thread — never blocks the camera)
- 💃 Dance for **10 continuous seconds** to silence it
- 📉 Progress bar decays if you stop moving for 2s — no cheating
- 😴 Snooze for 5 minutes or quit via keyboard
- 🎺 Victory tune plays when you earn your morning

</td>
<td width="50%" valign="top">

### 🖥️ Dashboard (Tkinter)
- ➕ Add alarms with time, label & Once/Daily repeat
- 📋 Alarm list with live status (ON / RINGING / snoozed)
- ✏️ Enable, disable and delete alarms
- 💾 Alarms persist across restarts (`alarms.json`)
- 🧪 "Test dance now" button — challenge yourself instantly

</td>
</tr>
</table>

---

## 🛠️ Tech Stack

<div align="center">
<img src="https://skillicons.dev/icons?i=python,git,github" />
</div>

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| Body Tracking | MediaPipe 1.x Tasks API (`PoseLandmarker`) |
| Camera & UI Overlay | OpenCV (`cv2.VideoCapture`, live skeleton + HUD) |
| GUI Dashboard | Tkinter / ttk |
| Alarm Sound | `winsound` (Windows built-in beeper) |
| Persistence | `json` (`alarms.json`) |
| Model | `pose_landmarker_lite.task` (float16, ~5.7 MB) |

---

## 🚀 Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/<your-username>/Move2Wake.git
cd Move2Wake
```

**2. Install dependencies**
```bash
pip install mediapipe opencv-python
```

**3. Run it**

Dashboard (recommended):
```bash
python alarm_gui.py
```

Or the quick CLI version:
```bash
python alarm.py 06:30      # rings at 06:30
python alarm.py --test 10  # rings in 10 seconds — try this first!
```

> **Tip:** On the very first run the pose model (`pose_landmarker_lite.task`) should sit next to the script — it is downloaded automatically during setup. In the camera window: **dance until the bar is full**, `S` = snooze 5 min, `Q` = quit.

---

## 🧠 How It Works

| Concept | Implementation |
|---|---|
| **Pose Detection** | MediaPipe `PoseLandmarker` runs in VIDEO mode on every frame, giving 33 normalized body landmarks |
| **Movement Score** | Mean per-frame displacement of all landmarks, normalized by shoulder width (distance-invariant), smoothed with an exponential moving average |
| **Dance Detection** | When the smoothed score crosses the threshold, the 10-second dance meter fills; idle for more than 2 seconds and the meter starts draining |
| **Alarm Ringing** | `winsound.Beep` alternates two tones inside a daemon thread until the dance succeeds or the user snoozes/quits |
| **Scheduling (GUI)** | Tkinter's `after()` polls every 500 ms and matches enabled alarms against the current HH:MM — each alarm fires once per day, with a 5-minute snooze timer |
| **Session Flow** | The dance window returns `success` / `snooze` / `quit`, so the GUI knows whether to disable a Once alarm, arm a snooze, or just stop |

---

## 📁 Project Structure

```
alarm_project/
├── alarm.py                       # ⏰ CLI alarm + ring/dance logic
├── alarm_gui.py                   # 🖥️ Tkinter dashboard (add/manage alarms)
├── pose_landmarker_lite.task      # 🤖 MediaPipe pose model (float16)
├── alarms.json                    # 💾 Saved alarms (auto-created by GUI)
└── README.md                      # 📖 You're here
```

---

## ⚙️ Tuning

| Setting | Where | Default | Meaning |
|---|---|---|---|
| `DANCE_TARGET_SECONDS` | `alarm.py` | `10.0` | Seconds of dancing required |
| `MOVE_THRESHOLD` | `alarm.py` | `0.07` | Movement sensitivity (lower = easier) |
| `SNOOZE_MINUTES` | `alarm.py` | `5` | Snooze duration |
| `IDLE_GRACE` | `alarm.py` | `2.0` | Idle seconds before the meter decays |

---

## 📈 Roadmap

- [ ] Custom alarm sounds (MP3/WAV instead of beeps)
- [ ] Dance-move challenges (raise your hands, spin, jump)
- [ ] Daily streak counter for early risers
- [ ] Cross-platform audio (drop `winsound` dependency)
- [ ] Config file for thresholds and snooze length

---

<div align="center">

### ⭐ Star this repo if Move2Wake finally got you out of bed!

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:F59E0B,100:EF4444&height=120&section=footer"/>

</div>
