# Collected Training Images

This directory stores nozzle detection images when `save_training_images: true` is enabled in your printer configuration.

## Purpose

These images are used for custom AI model training to improve detection accuracy for your specific nozzle setup.

## What Gets Saved

When a successful nozzle detection occurs:
- **Image file**: `YYYY-MM-DD_HH-MM-SS-mmm.jpg` (camera frame with detected nozzle)
- **Metadata file**: `YYYY-MM-DD_HH-MM-SS-mmm.json` (detection coordinates and confidence)

## Using These Images

1. **Collect 50-200 images** with `save_training_images: true`
2. **Annotate** them using Roboflow or Label Studio
3. **Train** a custom YOLOv8 model (see [Custom Model Training Guide](../docs/CUSTOM_MODEL_TRAINING.md))
4. **Deploy** your improved model to TAXY

## Privacy

All images are stored **locally on your Raspberry Pi** - nothing is sent to external servers.

## Cleanup

You can safely delete old images after training:
```bash
rm -rf /home/pi/TAXY/collected_images/*.jpg
rm -rf /home/pi/TAXY/collected_images/*.json
```
