# Reactive Signs Tracker 2026

Tracking template for an Intel RealSense camera and p5.js.

## 1. Start the tracker

On macOS:

```bash
cd python_realSenseOSC
./run.command
```

On Windows, double-click `python_realSenseOSC/run.bat`.

The first run creates a Python virtual environment and installs the required packages. A RealSense camera is used on Windows; on macOS the included demo recording is played.

## 2. Start the p5.js project

Open `p5js/index.html` in a local web server or with the VS Code Live Server extension.

The tracker sends position data over WebSocket on `ws://localhost:8025`. Keep the tracker running while using the p5.js sketch.

## 3. Edit the sketch

Create your animation in `p5js/sketch.js`.

For more tracker controls and OSC details, see `python_realSenseOSC/README.md`.
