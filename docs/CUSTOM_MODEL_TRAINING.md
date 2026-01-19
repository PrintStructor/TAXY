# Custom YOLOv8 Model Training for TAXY

This guide explains how to train a custom YOLOv8 model specifically for your nozzles, which will significantly improve detection accuracy compared to using a larger generic model.

## Why Custom Training?

- **Better than larger models**: A custom-trained YOLOv8n (12MB) will outperform a generic YOLOv8m (52MB)
- **Faster inference**: Keep the small model size for fast detection (~100-200ms)
- **Your specific conditions**: Trained on your nozzles, lighting, and camera setup
- **Continuous improvement**: Retrain as you collect more images

---

## Prerequisites

- Python 3.8+ with pip
- ~2GB disk space for training
- (Optional) Google Colab for free GPU training

---

## Step 1: Collect Training Images

### Method A: Automatic Collection (Recommended)

Enable local image collection in your `printer.cfg`:

```ini
[taxy]
save_training_images: true  # Temporarily enable to save images locally
```

Then run calibration normally. **All successful detections will be saved to `~/TAXY/collected_images/`** on your Raspberry Pi with metadata (coordinates, confidence).

**Privacy Note**: All images are stored locally - nothing is sent to external servers.

### Method B: Manual Collection

1. Enable preview mode:
   ```gcode
   START_PREVIEW_TAXY
   ```

2. Position each tool over camera and take snapshots:
   ```bash
   # Save snapshots from preview stream to collected_images
   mkdir -p ~/TAXY/collected_images
   curl http://192.168.178.188:8085/preview > ~/TAXY/collected_images/tool0_clean.jpg
   ```

3. Collect diverse images:
   - Clean nozzles
   - Dirty nozzles (filament residue)
   - Different angles (±5° tilt)
   - Different lighting conditions
   - All 6 tools

**Target**: 50-100 images minimum, 200+ images ideal

**Tip**: After collection, transfer images to your PC:
```bash
scp -r pi@your-pi-ip:~/TAXY/collected_images ./training_data
```

---

## Step 2: Annotate Images

Use [Roboflow](https://roboflow.com) (free tier is enough) or [Label Studio](https://labelstud.io/):

### Using Roboflow (Easiest)

1. Create account at https://roboflow.com
2. Create new project: "Nozzle Detection"
3. Upload your images
4. Draw bounding boxes around each nozzle
5. Label as "nozzle"
6. Generate dataset:
   - Format: **YOLOv8**
   - Split: 80% train, 15% valid, 5% test
   - Augmentation: Enable rotation, brightness, blur
7. Export → Download as ZIP

---

## Step 3: Train YOLOv8 Model

### Option A: Google Colab (Free GPU)

1. Open [Google Colab](https://colab.research.google.com/)
2. Create new notebook
3. Run training code:

```python
# Install Ultralytics YOLOv8
!pip install ultralytics

# Upload your Roboflow dataset.zip
from google.colab import files
uploaded = files.upload()
!unzip dataset.zip -d ./dataset

# Train model
from ultralytics import YOLO

# Start with pretrained YOLOv8n
model = YOLO('yolov8n.pt')

# Train on your nozzle dataset
results = model.train(
    data='./dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    patience=20,
    device=0  # GPU
)

# Export to ONNX
model.export(format='onnx', imgsz=640)

# Download best.onnx
from google.colab import files
files.download('./runs/detect/train/weights/best.onnx')
```

### Option B: Local Training (CPU - Slow)

```bash
# Install ultralytics
pip install ultralytics

# Train
yolo train model=yolov8n.pt data=/path/to/dataset/data.yaml epochs=100 imgsz=640

# Export
yolo export model=runs/detect/train/weights/best.pt format=onnx
```

**Training time**:
- Google Colab GPU: ~10-20 minutes
- Raspberry Pi 4 CPU: ~6-8 hours (not recommended)
- Desktop GPU (RTX 3060): ~5-10 minutes

---

## Step 4: Deploy Custom Model

1. Copy trained model to TAXY:
   ```bash
   scp best.onnx pi@192.168.178.188:~/TAXY/server/
   ```

2. Backup original model:
   ```bash
   mv ~/TAXY/server/best.onnx ~/TAXY/server/best.onnx.original
   mv ~/best.onnx ~/TAXY/server/best.onnx
   ```

3. Restart TAXY service:
   ```bash
   sudo systemctl restart taxy
   ```

4. Test detection:
   ```gcode
   START_PREVIEW_TAXY
   FIND_NOZZLE_CENTER_TAXY
   ```

---

## Step 5: Evaluate and Iterate

### Check Performance

Monitor detection success rate:
```gcode
# After calibration, check printer.taxy status
# In Mainsail console:
DUMP_STATE OBJECTS=taxy
```

Look for `last_nozzle_center_successful: true/false`

### Continuous Improvement

1. **Collect more data**: Keep `save_training_images: true` for a week to gather diverse scenarios
2. **Review collected images**: Check `~/TAXY/collected_images/` for challenging cases
3. **Add to dataset**: Annotate new edge cases
3. **Retrain**: Add new images to dataset and retrain
4. **Deploy**: Replace model and test

**Pro tip**: After 200+ images from your specific setup, detection should be near-perfect.

---

## Troubleshooting

### Model too slow

- Verify you exported with `imgsz=640` (not 1280)
- Check ONNX export settings (FP16 might not be supported on RPi)

### Detection worse than original

- Check annotation quality (boxes should be tight around nozzle)
- Increase training epochs (try 150-200)
- Add more diverse images (lighting, angles)
- Verify `data.yaml` has correct paths

### Out of memory during training

- Reduce batch size: `batch=8` or `batch=4`
- Use Google Colab instead of local training

---

## Advanced: Data Augmentation

When generating dataset in Roboflow, enable these augmentations:

- **Rotation**: ±15° (simulates camera misalignment)
- **Brightness**: ±20% (lighting variations)
- **Blur**: Up to 2px (focus issues)
- **Noise**: 5% (sensor noise)
- **Flip**: Horizontal only (vertical flip unrealistic)

This effectively 5x your dataset size without collecting more images.

---

## Example Training Metrics

After successful training, you should see:

```
Epoch   GPU_mem   box_loss   cls_loss   mAP50    mAP50-95
-----   -------   --------   --------   -----    --------
100/100  2.1G      0.523      0.178      0.96     0.72
```

**Good metrics**:
- mAP@0.5 > 0.95 (excellent)
- mAP@0.5 = 0.90-0.95 (good)
- mAP@0.5 < 0.90 (needs more data or training)

---

## Resources

- **Ultralytics YOLOv8 Docs**: https://docs.ultralytics.com/
- **Roboflow Tutorial**: https://roboflow.com/annotate
- **Training Guide**: https://docs.ultralytics.com/modes/train/
- **ONNX Export**: https://docs.ultralytics.com/modes/export/

---

## Questions?

Open an issue on GitHub: https://github.com/PrintStructor/TAXY/issues
