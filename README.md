# 🧭 TAXY – AI-Powered Tool Alignment for Klipper

<p align="center">
  <img src="https://img.shields.io/badge/Klipper-3D_Printer-blue" alt="Klipper">
  <img src="https://img.shields.io/badge/AI-YOLOv8-green" alt="YOLOv8">
  <img src="https://img.shields.io/badge/License-GPL--3.0-orange" alt="License">
</p>

**TAXY** (Tool Alignment XY) is an AI-powered system for automatic XY tool offset calibration on Klipper-based toolchanger 3D printers using a nozzle camera.

## 🌟 Why TAXY?

Traditional computer vision approaches (blob detection, thresholding) fail in challenging conditions:
- ❌ Dirty nozzles covered in filament residue
- ❌ Variable lighting and reflections
- ❌ Complex backgrounds (build plates, wiring)

**TAXY uses YOLOv8 deep learning** to detect nozzles robustly regardless of surface conditions.

---

## 🚀 Features

✅ **AI-Powered Detection**: YOLOv8 Nano model trained specifically on 3D printer nozzles
✅ **Camera Calibration**: Automatic mm-per-pixel calculation
✅ **Live Preview**: Real-time nozzle detection visualization in Mainsail/Fluidd
✅ **Tool Offset Measurement**: Precise XY offset calculation for multi-tool setups
✅ **Easy Installation**: One-command setup script
✅ **Klipper Integration**: Native GCode commands + status variables

---

## 📦 Installation

### Quick Install (Recommended)

```bash
cd ~
git clone https://github.com/PrintStructor/TAXY.git
cd TAXY
./install.sh
```

The installer will:
1. Install system dependencies (OpenCV, numpy, Flask, etc.)
2. Create Python virtual environment (`~/taxy-env`)
3. Install TAXY server as systemd service
4. Copy Klipper extension to `~/klipper/klippy/extras/`
5. Install macro files

### Manual Configuration

Add to your `printer.cfg`:

```ini
[taxy]
nozzle_cam_url: http://localhost/webcam/snapshot?max_delay=0
server_url: http://localhost:8085
move_speed: 1800
send_frame_to_cloud: false
detection_tolerance: 0

[include taxy-macros.cfg]
```

Restart Klipper:

```bash
sudo systemctl restart klipper
```

---

## 🎮 Usage

### Basic Workflow

1. **Send camera config to server**
   ```gcode
   SEND_SERVER_CFG_TAXY
   ```

2. **Start live preview** (view AI detection in Mainsail)
   ```gcode
   START_PREVIEW_TAXY
   ```

3. **Calibrate camera** (measure mm-per-pixel)
   ```gcode
   CALIB_CAMERA_TAXY
   ```

4. **Find nozzle center**
   ```gcode
   FIND_NOZZLE_CENTER_TAXY
   ```

5. **Save origin** (for reference tool)
   ```gcode
   SET_ORIGIN_TAXY
   ```

6. **Measure offset** (for other tools)
   ```gcode
   GET_OFFSET_TAXY
   ```

7. **Stop preview**
   ```gcode
   STOP_PREVIEW_TAXY
   ```

### Available Commands

| Command | Description |
|---------|-------------|
| `CALIB_CAMERA_TAXY` | Calibrate camera mm/px model |
| `START_PREVIEW_TAXY` | Start live AI detection preview |
| `STOP_PREVIEW_TAXY` | Stop preview |
| `FIND_NOZZLE_CENTER_TAXY` | Detect and move to nozzle center |
| `SET_ORIGIN_TAXY` | Save current position as origin |
| `GET_OFFSET_TAXY` | Calculate XY offset from origin |
| `SIMPLE_NOZZLE_POSITION_TAXY` | Get nozzle position (no move) |
| `SEND_SERVER_CFG_TAXY` | Send config to server |

---

## 🧠 AI Model

TAXY uses **YOLOv8n** (Nano) optimized for edge inference:

- **Model**: `best.onnx` (12MB)
- **Input**: 640×640 RGB images
- **Inference**: ONNX Runtime (CPU-optimized for Raspberry Pi)
- **Precision**: Sub-pixel center detection via bounding box
- **Fallback**: If model not found, falls back to traditional blob detection

### Model Performance

- **Detection Accuracy**: >95% on validation set
- **mAP@0.5**: 0.92
- **Inference Time**: ~100-200ms on Raspberry Pi 4

---

## 🔧 Troubleshooting

### Nozzle not detected
- Clean nozzle tip
- Adjust camera focus
- Check lighting (chamber LEDs OFF, nozzle LEDs RED recommended)
- Verify camera URL: `curl http://<IP>/webcam/snapshot?max_delay=0`

### Server not starting
```bash
sudo journalctl -u taxy -n 50
```

Common issues:
- Port 8085 already in use → stop conflicting service
- Missing dependencies → reinstall venv: `rm -rf ~/taxy-env && ./install.sh`

### "Unknown command: KTAY_*"
- Klipper extension not loaded
- Check: `ls ~/klipper/klippy/extras/taxy.py`
- Restart Klipper: `sudo systemctl restart klipper`

---

## 📚 Documentation

- [Calibration Guide](examples/atom-tc-6tool/CALIBRATION_GUIDE.md)
- [Migration from kTAMV](docs/MIGRATION_FROM_KTAMV.md)
- [AI vs Traditional CV Comparison](docs/AI_VS_CV_COMPARISON.md)

---

## 🙏 Credits

- **Original concept**: [kTAY8](https://github.com/DRPLAB-prj/kTAY8) by DRPLAB
- **Inspired by**: [kTAMV](https://github.com/TypQxQ/kTAMV) by TypQxQ
- **YOLOv8**: Ultralytics
- **Training dataset**: Community contributors + Roboflow Universe

---

## 🔒 License

GPL-3.0 License - See [LICENSE](LICENSE) for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

### Improving the AI Model

If TAXY fails to detect your nozzle:
1. Capture images via `send_frame_to_cloud: true` in config
2. Submit to model training dataset
3. Help improve detection for the entire community!

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/PrintStructor/TAXY/issues)
- **Discord**: [Voron Toolchangers](https://discord.gg/voron)

---

**Made with ❤️ for the 3D printing community**
