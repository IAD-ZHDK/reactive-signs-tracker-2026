# realSenseOSC (Python)

Python port of the Processing `realSenseOSC` app. It tracks blobs (people) in the depth image of an Intel RealSense camera and streams the depth image plus the tracked position as an OSC message over a websocket (`ws://localhost:8025/`, address `/depth`).

- **Windows:** uses the RealSense camera (`pyrealsense2`).
- **macOS / no camera found:** plays back the demo recording in `data/recordings/`. If that is missing, a simple animation is used.

## Run

Requires Python 3.

- macOS: double-click or run `./run.command` (once: `chmod +x run.command`)
- Windows: double-click `run.bat`

The first run creates a `.venv` and installs `requirements.txt`. Extra arguments are passed on to the app.

Manual start: `pip install -r requirements.txt` then `python realsense_osc.py`.

## Window

Red boxes show detected blobs (with ID), the blue dot is the averaged position, orange dots are the individual blobs. The cyan lines mark the crop area.

## Keys

| Key | Action |
|---|---|
| `e` | toggle edit mode (unlocks the distance slider and crop setting; locked otherwise) |
| `a`, then click | set crop top-left (edit mode) |
| `s`, then click | set crop bottom-right (edit mode) |
| `r` | toggle RGB streaming |
| `f` / `h` | flip vertically / horizontally |
| `q` / Esc | quit |

Settings (distance range, crop) are saved to `data/lowHigh.csv`.

## OSC message `/depth`

`int width, int height, blob depth (width*height bytes, grayscale), float x (mirrored: 1-x), float y, float z (closest point in the blob, 0 = far .. 1 = near), int tracking` and, if RGB streaming is on, three more blobs (R, G, B). Positions are normalized to the crop area.

## Recording demo footage (hidden)

Press `Shift+R` in the window (or start with `--record`) to start or stop saving depth frames to `data/recordings/outputImageN.jpg`. A red dot shows while recording. Recording restarts at `outputImage0.jpg` and overwrites old frames. At least 20 frames are needed for playback.
