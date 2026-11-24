# OSC position helper

A small browser library for using an OSC `x`, `y`, and optional `z` position in
p5.js sketches.

## Install and build

```bash
npm install
npm run build
```

Use `npm start` for the development server at `http://localhost:8080`.

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
  poster.setup();
}

function draw() {
  const { x, y, z } = poster.position;
  circle(x * width, y * height, z * 100);
}
```

`poster.x`, `poster.y`, `poster.z`, and the `poster.posNormal` alias are also
available. Use `poster.hasOSCSignal()` to check whether a position was received
recently.

It connects to `ws://localhost:8025` and exposes a mutable normalized position.
If no fresh OSC signal is available, moving the mouse updates `x` and `y`
instead. The library checks for a restored WebSocket connection every two
seconds and resumes OSC control as soon as a new position arrives.

To change the WebSocket endpoint, pass options to `poster.setup()`:

```js
poster.setup({
  host: 'localhost',
  port: 9000,
  address: '/position',
  retryInterval: 2000,
  signalTimeout: 2000
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
