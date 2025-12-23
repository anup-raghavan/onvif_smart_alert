# ONVIF Face Recognition & Alexa Integration

## Overview
This Python application connects to ONVIF-enabled IP cameras or NVRs to display live video streams. It performs real-time face detection and recognition, and can trigger external actions (like Alexa announcements) via webhooks when a known person is identified.

## Features
*   **ONVIF Support**: Connects to cameras/NVRs to authorize and retrieve stream URIs.
*   **Face Detection**: Detects faces in the live video feed using OpenCV.
*   **Face Recognition**: Identifies specific individuals using a trained LBPH model (`opencv-contrib-python`).
*   **Multi-Person Support**: Can be trained on multiple different people to distinguish between them.
*   **Alexa/Webhook Integration**: Triggers a customizable webhook URL (e.g., Voice Monkey) when a recognized face is detected.
*   **Robustness**: Optimized for RTSP over TCP, automatic reconnection, and main-thread execution stability.

## Prerequisites
*   **OS**: Windows 10/11 (Recommended) or Linux.
*   **Python**: 3.10 or higher.
*   **Dependencies**:
    *   `opencv-contrib-python` (Essential for face recognition modules)
    *   `onvif-zeep` (For ONVIF communication)
    *   `numpy`

## Installation

1.  **Clone or Download** this project folder.
2.  **Install Python Dependencies**:
    Open your terminal/command prompt and run:
    ```bash
    pip install opencv-contrib-python onvif-zeep numpy
    ```

## Usage

### 1. Training Mode (Capture Faces)
First, you need to "teach" the system what you look like. Run the app in training mode to capture images.

```bash
python main.py --ip <IP> --port <PORT> --user <USER> --password <PASS> --train "YourName"
```
*   **Example**: `python main.py --ip 192.168.1.100 --port 80 --user admin --password secret --train "John"`
*   The video stream will open.
*   When your face is clearly visible, **press 'c'** to capture a photo.
*   Capture **20-30 images** with different expressions and angles.
*   **Press 'q'** to exit when done.

### 2. Train the Model
After capturing images for one or more people, you must run the trainer script to compile the data into a recognition model.

```bash
python trainer.py
```
*   This will scan the `dataset/` folder.
*   It generates two files: `trainer.yml` (The model) and `names.json` (ID mapping).

### 3. Run Recognition
Now you can run the application normally. It will automatically detect and recognize faces.

```bash
python main.py --ip <IP> --port <PORT> --user <USER> --password <PASS> --webhook-url "YOUR_WEBHOOK_URL"
```
*   **--webhook-url**: (Optional) A URL to notify when a person is recognized. 
    *   If using **Voice Monkey**, the app automatically appends `&text=Name is at the door` to the URL.
*   **--channel**: (Optional) If using an NVR, specify the channel number (e.g., `--channel 1`).

## Example Workflow
1.  **Capture John**: `python main.py ... --train "John"` (Press 'c' 20 times)
2.  **Capture Jane**: `python main.py ... --train "Jane"` (Press 'c' 20 times)
3.  **Train**: `python trainer.py`
4.  **Run**: `python main.py ...` -> Detects John or Jane and prints their name on screen.

## Troubleshooting

### "Unknown C++ Exception" or Freeze
Ensure you are using the latest version of `stream_player.py`. We recently moved the video loop to the **Main Thread** to fix GUI freezing issues on Windows.

### "No module named cv2.face"
You likely installed `opencv-python` instead of `opencv-contrib-python`. Uninstall the standard one and install the contrib version:
```bash
pip uninstall opencv-python
pip install opencv-contrib-python
```

### Recognition Accuracy
*   If the system doesn't recognize you, capture more images with better lighting.
*   If it mistakes strangers for you, you can adjust the confidence threshold in `stream_player.py` (Search for `if confidence < 45:`). Lower is stricter.
