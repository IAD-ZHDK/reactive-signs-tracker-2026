"""
realSenseOSC (Python version)
Sends x/y/z tracking data from an Intel RealSense camera as OSC over a websocket.
Port of the Processing app by Florian Bruggisser / Luke Franzke (Reactive Signs, ZHdK).

The RealSense camera is only used on Windows. On macOS (or if no camera is found)
the recorded demo images in data/recordings are played back instead.

Keys (window must be focused):
  e   toggle "allow edits" (distance sliders + crop area)
  a   then click: set crop top-left      (edit mode)
  s   then click: set crop bottom-right  (edit mode)
  f   toggle vertical flip
  h   toggle horizontal flip
  q / Esc  quit
Hidden: Shift+R (or --record) records the depth image to data/recordings.
"""
import argparse
import asyncio
import csv
import math
import os
import platform
import struct
import threading
import time

import cv2
import numpy as np

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REC_DIR = os.path.join(DATA_DIR, "recordings")
CSV_FILE = os.path.join(DATA_DIR, "lowHigh.csv")

WIDTH, HEIGHT = 640, 480
DECIMATION = 4
SMALL_W, SMALL_H = WIDTH // DECIMATION, HEIGHT // DECIMATION
PORT = 8025
WINDOW = "Realsense 2 WebSocket"
MIN_DISTANCE, MAX_DISTANCE = 0.0, 10.0


# ---------------------------------------------------------------- OSC
def _pad(b):
    return b + b"\0" * (-len(b) % 4)


def _osc_str(s):
    return _pad(s.encode() + b"\0")


def osc_message(address, args):
    """Encode an OSC message. args: int, float or bytes (blob)."""
    tags, data = ",", b""
    for a in args:
        if isinstance(a, (bytes, bytearray)):
            tags += "b"
            data += struct.pack(">i", len(a)) + _pad(bytes(a))
        elif isinstance(a, (bool, int, np.integer)):
            tags += "i"
            data += struct.pack(">i", int(a))
        else:
            tags += "f"
            data += struct.pack(">f", float(a))
    return _osc_str(address) + _osc_str(tags) + data


# ---------------------------------------------------------------- websocket server
class WSServer:
    def __init__(self, port):
        self.clients = set()
        self.loop = asyncio.new_event_loop()
        self.ok = websockets is not None
        if self.ok:
            self.port = port
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        asyncio.set_event_loop(self.loop)

        async def handler(ws, *_):
            self.clients.add(ws)
            try:
                async for _ in ws:
                    pass
            finally:
                self.clients.discard(ws)

        async def main():
            async with websockets.serve(handler, "0.0.0.0", self.port):
                await asyncio.Future()

        try:
            self.loop.run_until_complete(main())
        except Exception as ex:
            print("Error starting up websocket:", ex)
            self.ok = False

    def send(self, data):
        if not self.ok or not self.clients:
            return

        async def _send():
            for c in list(self.clients):
                try:
                    await c.send(data)
                except Exception:
                    self.clients.discard(c)

        asyncio.run_coroutine_threadsafe(_send(), self.loop)


# ---------------------------------------------------------------- camera
class RealSense:
    """Wraps pyrealsense2 (Windows only)."""

    def __init__(self, low, high):
        import pyrealsense2 as rs

        self.rs = rs
        if not rs.context().query_devices().size():
            raise RuntimeError("no realsense device found")
        self.pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, 30)
        cfg.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, 30)
        self.pipe.start(cfg)
        self.align = rs.align(rs.stream.color)
        self.threshold = rs.threshold_filter(low, high)
        self.decimation = rs.decimation_filter(DECIMATION)
        self.temporal = rs.temporal_filter()
        self.holes = rs.hole_filling_filter()
        self.colorizer = rs.colorizer()
        self.colorizer.set_option(rs.option.color_scheme, 2)  # white to black

    def set_range(self, low, high):
        self.threshold.set_option(self.rs.option.min_distance, low)
        self.threshold.set_option(self.rs.option.max_distance, high)

    def read(self):
        """Returns (depth BGR image, color BGR image at small size)."""
        frames = self.align.process(self.pipe.wait_for_frames(5000))
        depth = frames.get_depth_frame()
        for f in (self.threshold, self.decimation, self.temporal, self.holes):
            depth = f.process(depth)
        depth_img = np.asanyarray(self.colorizer.colorize(depth).get_data())
        color = np.asanyarray(frames.get_color_frame().get_data())
        color = cv2.resize(color, (depth_img.shape[1], depth_img.shape[0]))
        return depth_img.copy(), color

    def stop(self):
        try:
            self.pipe.stop()
        except Exception:
            pass


# ---------------------------------------------------------------- app
class App:
    def __init__(self, record=False):
        self.low, self.high = MIN_DISTANCE, MAX_DISTANCE
        self.crop_y, self.crop_h, self.crop_x, self.crop_w = 0.3, 0.5, 0.05, 0.9
        self.load_settings()
        self.editable = False
        self.flip = False
        self.horizontal = True
        self.recording = record
        self.record_count = 0
        self.pending_click = None
        self.saved_at = 0.0
        self.camera = None
        self.next_camera_try = 0
        self.frames = self.load_recording()
        self.frame_count = 0
        self.tracking = False
        self.blobs = []
        self.last_tracking = 0.0
        self.filter_ratio = 0.95
        self.single = np.zeros(3)
        self.multi = [np.zeros(3)]
        self.ws = WSServer(PORT)
        self.fps = 0.0

    # settings
    def load_settings(self):
        try:
            with open(CSV_FILE, newline="") as f:
                row = next(csv.DictReader(f))
            self.low, self.high = float(row["low"]), float(row["high"])
            self.crop_y, self.crop_h = float(row["cropY"]), float(row["cropHeight"])
            self.crop_x, self.crop_w = float(row["cropX"]), float(row["cropWidth"])
        except (OSError, StopIteration, KeyError, ValueError):
            print("no csv file found, creating one")
            self.save_settings()

    def save_settings(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp = CSV_FILE + ".tmp"
            with open(tmp, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["low", "high", "cropY", "cropHeight", "cropX", "cropWidth"])
                w.writerow([self.low, self.high, self.crop_y, self.crop_h, self.crop_x, self.crop_w])
            os.replace(tmp, CSV_FILE)
            self.saved_at = time.time()
            print("saved settings to", CSV_FILE)
        except OSError as ex:
            print("ERROR saving settings:", ex)

    # demo footage
    def load_recording(self):
        frames = []
        i = 0
        while True:
            img = cv2.imread(os.path.join(REC_DIR, "outputImage%d.jpg" % i))
            if img is None:
                break
            frames.append(img)
            i += 1
        if len(frames) < 20:
            print("no demo recording found, using animation")
            return []
        print("loaded %d demo frames" % len(frames))
        return frames

    # camera handling (Windows only)
    def try_camera(self):
        if platform.system() != "Windows" or time.time() < self.next_camera_try:
            return
        self.next_camera_try = time.time() + 5
        try:
            self.camera = RealSense(self.low, self.high)
            print("realsense started")
        except Exception as ex:
            self.camera = None
            print("no realsense camera, playing demo:", ex)

    def get_frames(self):
        """Returns (depth, rgb, live)."""
        if self.camera is None:
            self.try_camera()
        if self.camera is not None:
            try:
                depth, rgb = self.camera.read()
                if self.flip:
                    depth, rgb = cv2.flip(depth, 0), cv2.flip(rgb, 0)
                if self.horizontal:
                    depth, rgb = cv2.flip(depth, 1), cv2.flip(rgb, 1)
                return depth, rgb, True
            except Exception as ex:
                print("camera error:", ex)
                self.camera.stop()
                self.camera = None
        if self.frames:
            img = self.frames[self.frame_count % len(self.frames)]
            return img.copy(), img.copy(), False
        return self.animation_frame(), None, False

    def animation_frame(self):
        ys, xs = np.mgrid[0:SMALL_H, 0:SMALL_W]
        dist = np.hypot(xs - WIDTH / 2, ys - HEIGHT / 2)
        angle = np.radians(self.frame_count - dist) * 1.5
        g = np.clip(np.floor(np.sin(angle) * 127) + 127, 0, 255).astype(np.uint8)
        return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

    # tracking
    def crop(self, img):
        h, w = img.shape[:2]
        x, y = int(w * self.crop_x), int(h * self.crop_y)
        return img[y : y + int(h * self.crop_h), x : x + int(w * self.crop_w)]

    def blob_tracking(self, depth_crop):
        g = cv2.cvtColor(depth_crop, cv2.COLOR_BGR2GRAY)
        g = cv2.convertScaleAbs(g, alpha=1.3)
        k = np.ones((3, 3), np.uint8)
        g = cv2.dilate(g, k)
        g = cv2.blur(g, (5, 5))
        g = cv2.erode(g, k, iterations=3)
        contours, _ = cv2.findContours(g, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        return [cv2.boundingRect(c) for c in contours]

    def find_positions(self, rects, depth_crop):
        crop_h, crop_w = depth_crop.shape[:2]
        gray = depth_crop[:, :, 0]
        point = np.array([0.5, 0.5, 0.01])
        found = []
        self.blobs = []
        for (x, y, w, h) in rects:
            if (w + h) / 2 * DECIMATION >= 100:
                self.blobs.append((x, y, w, h, crop_w, crop_h))
                # z: closest point in the blob (white = near), 0..1
                z = float(gray[y : y + h, x : x + w].max()) / 255.0
                found.append(np.array([(x + w / 2) / crop_w, (y + h / 2) / crop_h, z]))
        if found:
            self.tracking = True
            self.last_tracking = time.time()
            point = np.mean(found, axis=0)
            self.filter_ratio = 0.90
            found.sort(key=lambda p: p[0])
            self.multi = sorted(self.multi, key=lambda p: p[0])[: len(found)]
            for i, p in enumerate(found):
                if i < len(self.multi):
                    self.multi[i] = self.multi[i] * 0.9 + p * 0.1
                else:
                    self.multi.append(p.copy())
        else:
            if time.time() > self.last_tracking + 0.4:
                self.tracking = False
            self.filter_ratio = 0.90
        self.single = self.single * self.filter_ratio + point * (1 - self.filter_ratio)

    # output
    def send(self, label="/position"):
        args = [1.0 - self.single[0], self.single[1], self.single[2]]
        self.ws.send(osc_message(label, args))

    def draw(self, depth, live):
        canvas = cv2.resize(depth, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
        accent = (0xCF, 0xA2, 0x08) if self.editable else (0x52, 0x36, 0x00)
        x0, y0 = int(WIDTH * self.crop_x), int(HEIGHT * self.crop_y)
        x1, y1 = x0 + int(WIDTH * self.crop_w), y0 + int(HEIGHT * self.crop_h)
        for p, q in (((0, y0), (WIDTH, y0)), ((0, y1), (WIDTH, y1)),
                     ((x0, 0), (x0, HEIGHT)), ((x1, 0), (x1, HEIGHT))):
            cv2.line(canvas, p, q, accent, 1)

        def pt(v):
            return (int(x0 + v[0] * (x1 - x0)), int(y0 + v[1] * (y1 - y0)))

        for i, (bx, by, bw, bh, cw, ch) in enumerate(self.blobs):
            p1 = (int(x0 + bx / cw * (x1 - x0)), int(y0 + by / ch * (y1 - y0)))
            p2 = (int(x0 + (bx + bw) / cw * (x1 - x0)), int(y0 + (by + bh) / ch * (y1 - y0)))
            cv2.rectangle(canvas, p1, p2, (0, 0, 255), 2)
            cv2.putText(canvas, "ID: %d" % i, (p1[0] + 5, p1[1] + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.circle(canvas, pt(self.single), 6, (0xCF, 0xA2, 0x08), -1)
        for v in self.multi:
            cv2.circle(canvas, pt(v), 4, (0, 100, 255), -1)

        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (WIDTH, 130), (55, 55, 55), -1)
        canvas = cv2.addWeighted(overlay, 0.4, canvas, 0.6, 0)
        lines = ["Image Size: %d x %d" % (SMALL_W, SMALL_H),
                 "Serving: ws://localhost:%d/" % PORT,
                 "trackingActive: %s  (%s)" % (self.tracking, "camera" if live else "demo"),
                 "cameraFlip: %s" % self.flip]
        for i, t in enumerate(lines):
            cv2.putText(canvas, t, (20, 25 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        if self.editable:
            for i, t in enumerate(["'a' then click: top-left", "'s' then click: btm-right"]):
                cv2.putText(canvas, t, (360, 25 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0xCF, 0xA2, 0x08), 1, cv2.LINE_AA)
        if time.time() - self.saved_at < 2:
            cv2.putText(canvas, "settings saved", (20, HEIGHT - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        if self.recording:
            cv2.circle(canvas, (WIDTH - 20, 20), 6, (0, 0, 255), -1)
        return canvas

    # ui
    def on_mouse(self, event, x, y, *_):
        if event != cv2.EVENT_LBUTTONDOWN or not (self.editable and self.pending_click):
            return
        try:
            _, _, ww, wh = cv2.getWindowImageRect(WINDOW)
            if ww > 0 and wh > 0:
                x, y = x * WIDTH / ww, y * HEIGHT / wh
        except cv2.error:
            pass
        if self.pending_click == "a":
            self.crop_y, self.crop_x = y / HEIGHT, x / WIDTH
        else:
            self.crop_h = max(0.05, y / HEIGHT - self.crop_y)
            self.crop_w = max(0.05, x / WIDTH - self.crop_x)
        self.pending_click = None
        self.save_settings()

    def poll_range(self):
        """Read the sliders every frame (more reliable than callbacks)."""
        low = cv2.getTrackbarPos("low (cm)", WINDOW) / 100
        high = cv2.getTrackbarPos("high (cm)", WINDOW) / 100
        if not self.editable:
            # sliders are locked unless edit mode is on
            cv2.setTrackbarPos("low (cm)", WINDOW, int(round(self.low * 100)))
            cv2.setTrackbarPos("high (cm)", WINDOW, int(round(self.high * 100)))
            return
        if low >= high:
            high = low + 0.01
        if abs(low - self.low) > 1e-6 or abs(high - self.high) > 1e-6:
            self.low, self.high = low, high
            if self.camera:
                self.camera.set_range(low, high)
            self.save_settings()

    def run(self):
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, WIDTH, HEIGHT)
        cv2.setMouseCallback(WINDOW, self.on_mouse)
        cv2.createTrackbar("low (cm)", WINDOW, int(self.low * 100), int(MAX_DISTANCE * 100), lambda _: None)
        cv2.createTrackbar("high (cm)", WINDOW, int(self.high * 100), int(MAX_DISTANCE * 100), lambda _: None)
        print("Sending data on: ws://localhost:%d/" % PORT)
        if self.recording:
            os.makedirs(REC_DIR, exist_ok=True)
        last = time.time()
        while True:
            depth, rgb, live = self.get_frames()
            depth_crop = self.crop(depth)
            if live or self.frames:
                rects = self.blob_tracking(depth_crop)
                self.find_positions(rects, depth_crop)
            else:
                self.single = np.array([math.sin(math.radians(self.frame_count)) * 0.3 + 0.5, 0.5, 0.5])
            self.send()
            cv2.imshow(WINDOW, self.draw(depth, live))
            if self.recording:
                cv2.imwrite(os.path.join(REC_DIR, "outputImage%d.jpg" % self.record_count), depth)
                self.record_count += 1
            self.frame_count += 1
            self.poll_range()

            key = cv2.waitKey(max(1, int(1000 / 30 - (time.time() - last) * 1000))) & 0xFF
            last = time.time()
            if key in (27, ord("q")):
                break
            elif key == ord("e"):
                self.editable = not self.editable
            elif key in (ord("a"), ord("s")):
                self.pending_click = chr(key)
            elif key == ord("f"):
                self.flip = not self.flip
            elif key == ord("h"):
                self.horizontal = not self.horizontal
            elif key == ord("R"):  # hidden: record demo footage
                self.recording = not self.recording
                if self.recording:
                    os.makedirs(REC_DIR, exist_ok=True)
                    self.record_count = 0
                print("recording:", self.recording)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
        self.save_settings()
        if self.camera:
            self.camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help=argparse.SUPPRESS)
    App(record=ap.parse_args().record).run()
