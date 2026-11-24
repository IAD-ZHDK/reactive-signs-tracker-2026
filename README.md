# Reactive Signs Tracker 2026

Tracking template for an Intel RealSense camera and p5.js.

## 1. Install with Git

Install Git if it is not already available:

```bash
# macOS
brew install git

# Windows
winget install --id Git.Git -e
```

Then clone the project:

```bash
git clone https://github.com/IAD-ZHDK/reactive-signs-tracker-2026.git
cd reactive-signs-tracker-2026
```

## 2. Install Python

Install Python 3 if it is not already available:

```bash
# macOS
brew install python

# Windows
winget install --id Python.Python.3.11 -e
```

Close and reopen the terminal after installation, then verify it:

```bash
# macOS
python3 --version

# Windows
py --version
```

## 3. Start the tracker

On macOS:

```bash
cd python_realSenseOSC
./run.command
```

On Windows, double-click `python_realSenseOSC/run.bat`.

The first run creates a Python virtual environment and installs the required packages. A RealSense camera is used on Windows; on macOS the included demo recording is played.

## 4. Start the p5.js project

Open `p5js/index.html` in a local web server or with the VS Code Live Server extension.

The tracker sends position data over WebSocket on `ws://localhost:8025`. Keep the tracker running while using the p5.js sketch.

## 5. Edit the sketch

Create your animation in `p5js/sketch.js`.

For more tracker controls and OSC details, see `python_realSenseOSC/README.md`.
