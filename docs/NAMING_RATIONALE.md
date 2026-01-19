# 🧭 TAXY – Tool Alignment XY (Nozzle-Cam Calibration for Klipper)

> **TAXY** is a Klipper extension + server that uses a **nozzle camera** to help calibrate **XY tool offsets** (toolchangers) and assist with **nozzle centering** and **camera-to-mm calibration**.

This README documents **our changes** compared to the original upstream `kTAY8` template, includes the **new project name**, and provides **macro naming suggestions** that work cleanly in Klipper.

---

## ✅ Why we renamed kTAY8 → TAXY

The original project name was **kTAY8** (Klipper Tool Alignment XY, variant “8”).
While the idea is cool, the **“8” inside the Klipper command names** caused a hard issue.

### Problem: `KTAY8_*` commands caused `Malformed command`
Klipper parses commands like **letters + number** as a special token (similar to how `G1`, `M104`, etc. work).
So a command like:

```
KTAY8_START_PREVIEW
```

can be interpreted as:

- command token: `KTAY8`
- leftover: `_START_PREVIEW` → ❌ **Malformed**

### Fix: register commands without the digit
We switched to:

✅ `KTAY_*` → (or optionally `TAXY_*` as a future improvement)

Example:

- `KTAY_START_PREVIEW`
- `KTAY_SEND_SERVER_CFG`

This completely avoids the malformed parsing and works reliably in Klipper.

---

## ✅ Overview: Components

TAXY consists of two parts:

### 1) Klipper extension
Registers custom commands in Klipper and exposes status values.

Location (recommended):
```
~/klipper/klippy/extras/ktay8.py
~/klipper/klippy/extras/ktay8_utl.py
```

### 2) TAXY server (camera + detection backend)
A Python server that runs on the host (Raspberry Pi, etc.) and provides endpoints like:

- `/set_server_cfg`
- `/preview`
- nozzle detection pipeline

---

## ✅ Our GitHub-template changes (what we changed)

### ✅ 1) Fixed Klipper command naming: `KTAY8_*` → `KTAY_*`

We patched the extension to register safe command names in `handle_ready()`.

**Before (upstream):**
- `KTAY8_CALIB_CAMERA`
- `KTAY8_START_PREVIEW`
- `KTAY8_SEND_SERVER_CFG`
- …

**After (ours):**
- `KTAY_CALIB_CAMERA`
- `KTAY_START_PREVIEW`
- `KTAY_SEND_SERVER_CFG`
- `KTAY_STOP_PREVIEW`
- `KTAY_FIND_NOZZLE_CENTER`
- `KTAY_SIMPLE_NOZZLE_POSITION`
- `KTAY_SET_ORIGIN`
- `KTAY_GET_OFFSET`

✅ Result: No more `Malformed command ...`

---

### ✅ 2) Ensured Klipper loads the correct extension using Symlinks

We found that the **symlink into Klipper extras was missing**, so Klipper didn’t load the updated code.

We now recommend symlinking the repo’s extension into Klipper:

```bash
sudo rm -f ~/klipper/klippy/extras/ktay8.py
sudo ln -s /home/pi/kTAY8/extension/ktay8.py ~/klipper/klippy/extras/ktay8.py

sudo rm -f ~/klipper/klippy/extras/ktay8_utl.py
sudo ln -s /home/pi/kTAY8/extension/ktay8_utl.py ~/klipper/klippy/extras/ktay8_utl.py
```

✅ Result: edits in the repo immediately apply to Klipper after `RESTART`

---

### ✅ 3) Updated macros to call the new `KTAY_*` commands

Old macros called:
- `KTAY8_START_PREVIEW`, `KTAY8_SEND_SERVER_CFG`, …

New macros call:
- `KTAY_START_PREVIEW`, `KTAY_SEND_SERVER_CFG`, …

✅ Result: No more `Unknown command:"KTAY_*"` once extension is patched and linked.

---

### ✅ 4) Optional: Compatibility wrapper macro (nice-to-have)
If you ever have old UI buttons or scripts that still send `KTAY8` or `KTAY8_*`, you can add a compatibility macro.

Example:

```ini
[gcode_macro KTAY8]
description: Compatibility wrapper (catches old/invalid KTAY8 calls)
gcode:
  RESPOND TYPE=error MSG="KTAY8 base command called. Use KTAY_* commands instead."
```

---

## ✅ Suggested Macro Naming (Recommended)

You have two good options:

---

### Option A (keep your current style – easy migration)
Keep the *macro names* as `*_KTAY8`, but internally call `KTAY_*`.

✅ Pros: your UI buttons / muscle memory stay the same
✅ Cons: still visually contains “KTAY8”

Example file: `ktay8-macros.cfg`

```ini
[gcode_macro SEND_SERVER_CFG_KTAY8]
gcode:
  KTAY_SEND_SERVER_CFG

[gcode_macro START_PREVIEW_KTAY8]
gcode:
  KTAY_START_PREVIEW

[gcode_macro STOP_PREVIEW_KTAY8]
gcode:
  KTAY_STOP_PREVIEW
```

---

### Option B (clean rename – match the new project name)
Rename macros to `*_TAXY` so it reads clean and consistent.

✅ Pros: consistent branding, clear intent
✅ Cons: you’ll update UI buttons once

Recommended:

| What it does | Macro name |
|---|---|
| send server config | `TAXY_SEND_SERVER_CFG` |
| start preview | `TAXY_START_PREVIEW` |
| stop preview | `TAXY_STOP_PREVIEW` |
| detect nozzle | `TAXY_SIMPLE_NOZZLE_POSITION` |
| calibrate camera mm/px | `TAXY_CALIB_CAMERA` |
| find nozzle center | `TAXY_FIND_NOZZLE_CENTER` |
| save origin center | `TAXY_SET_ORIGIN` |
| get offset | `TAXY_GET_OFFSET` |

Example macros:

```ini
[gcode_macro TAXY_SEND_SERVER_CFG]
gcode:
  KTAY_SEND_SERVER_CFG

[gcode_macro TAXY_START_PREVIEW]
gcode:
  KTAY_START_PREVIEW

[gcode_macro TAXY_STOP_PREVIEW]
gcode:
  KTAY_STOP_PREVIEW

[gcode_macro TAXY_CALIB_CAMERA]
gcode:
  KTAY_CALIB_CAMERA

[gcode_macro TAXY_FIND_NOZZLE_CENTER]
gcode:
  KTAY_FIND_NOZZLE_CENTER

[gcode_macro TAXY_SIMPLE_NOZZLE_POSITION]
gcode:
  KTAY_SIMPLE_NOZZLE_POSITION

[gcode_macro TAXY_SET_ORIGIN]
gcode:
  KTAY_SET_ORIGIN

[gcode_macro TAXY_GET_OFFSET]
gcode:
  KTAY_GET_OFFSET
  TAXY_PRINT_OFFSET
```

And a helper macro to show offsets:

```ini
[gcode_macro TAXY_PRINT_OFFSET]
gcode:
  {action_respond_info("TAXY offset X:" ~ printer.ktay8.last_calculated_offset[0] ~ " Y:" ~ printer.ktay8.last_calculated_offset[1])}
```

---

## ✅ Suggested Calibration Workflow (Quick Start)

### 1) Send server configuration (camera URL)
```
TAXY_SEND_SERVER_CFG
```

or if you kept legacy macro names:
```
SEND_SERVER_CFG_KTAY8
```

### 2) Start live preview
```
TAXY_START_PREVIEW
```

### 3) Check nozzle detection
```
TAXY_SIMPLE_NOZZLE_POSITION
```

### 4) Calibrate camera mm-per-pixel model
```
TAXY_CALIB_CAMERA
```

### 5) Find nozzle center
```
TAXY_FIND_NOZZLE_CENTER
```

### 6) Set origin (save camera center position)
```
TAXY_SET_ORIGIN
```

### 7) Get offsets from origin
```
TAXY_GET_OFFSET
```

### 8) Stop preview
```
TAXY_STOP_PREVIEW
```

---

## ✅ Notes / Tips

- If nozzle detection fails: clean nozzle, adjust lighting, adjust Z height, verify camera focus.
- If calibration wants to move outside the camera frame: recalibrate mm/px or reduce calibration step size.
- Ensure your server is reachable:
  ```bash
  curl http://<YOUR_IP>:8085/
  ```
  Expect:
  `kTAY8 Server is running` (server page)

---

## ✅ Future Improvement (Optional)
To make everything fully consistent, we can also rename the internal Klipper commands from `KTAY_*` to `TAXY_*` inside the extension.

That would register commands like:
- `TAXY_START_PREVIEW`
- `TAXY_SEND_SERVER_CFG`
- …

…but it requires a second rename pass in the extension and macros.
Our current solution already works perfectly and keeps changes minimal.

---

## ✅ Credits
Original project concept based on upstream `kTAY8`.
This fork/variant **TAXY** focuses on clean Klipper command compatibility, stable loading via symlinks, and consistent macro naming.
