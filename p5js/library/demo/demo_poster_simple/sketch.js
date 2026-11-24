// LED wall: 2 columns x 6 rows, each panel 240 x 240 px
const PANEL = 240;
const COLS = 2;
const ROWS = 6;

function setup() {
  poster.setup();
  createCanvas(COLS * PANEL, ROWS * PANEL);
}

function draw() {
  const { x, y, z } = poster.position;

  background(0); // black
  noStroke();

  // one circle per panel, rising and falling in a wave across the wall
  for (let col = 0; col < COLS; col++) {
    for (let row = 0; row < ROWS; row++) {
      const phase = row * 0.8 + col * 0.4 + x;
      const size = PANEL * (0.2 + z * 0.2) * (1 + sin(frameCount * 0.05 + phase));
      fill(y * 255);
      circle(col * PANEL + PANEL / 2, row * PANEL + PANEL / 2, size);
    }
  }
  fill(255, 0, 0);
  circle(x, y, z)
}
