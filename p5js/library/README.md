# OSC position helper

A small browser library for using an OSC `x`, `y`, and optional `z` position in
p5.js sketches.

## Install and build

```bash
npm install
npm run build
```

Use `npm start` for the development server. It selects an available port and
prints the local URL in the terminal.

## Use

Load `dist/Poster_Control.js` before your sketch:

```html
<script src="Poster_Control.js"></script>
<script src="sketch.js"></script>
```

Call `poster.setup()` once from p5's setup function:

```js
function setup() {
  createCanvas(windowWidth, windowHeight);
  poster.setup({ resize: true });
}

function draw() {
  const { x, y, z } = poster.position;
  circle(x, y, z * 100);
}
```

After the canvas is created, the library records its original aspect ratio.
It automatically fits the canvas inside the viewport on window and fullscreen
changes without stretching it. Set `resize: false` to keep the original canvas
dimensions.

`poster.position` uses canvas pixel coordinates. `poster.posNormal`,
`poster.x`, `poster.y`, and `poster.z` use values normalized to `0–1`. Use
`poster.hasOSCSignal()` to check whether a position was received recently.

It connects to `ws://localhost:8025`. Without a fresh OSC signal,
`poster.position.x` and `poster.position.y` match p5.js `mouseX` and `mouseY`.
The library continues checking for restored OSC connections and immediately
resumes OSC control when a new position arrives.

To change the WebSocket endpoint, pass options to `poster.setup()`:

```js
poster.setup({
  host: 'localhost',
  port: 9000,
  address: '/position',
  retryInterval: 2000,
  signalTimeout: 2000,
  resize: false
});
```

## OSC messages

The preferred message is:

```text
/position <float x> <float y> [float z]
```

Separate `/x`, `/y`, and `/z` messages containing one float are supported too.
Legacy `/depth` messages are accepted when the values occupy arguments 4-6;
image data is ignored.
