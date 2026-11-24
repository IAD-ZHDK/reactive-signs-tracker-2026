// LED wall: 2 columns x 6 rows, each panel 240 x 240 px
const PANEL = 240;
const COLS = 2;
const ROWS = 6;

function setup() {
  createCanvas(COLS * PANEL, ROWS * PANEL);
}

function draw() {
  background(0); // black
  noStroke();
  fill(255); // white

  // one circle per panel, rising and falling in a wave across the wall
  for (let col = 0; col < COLS; col++) {
    for (let row = 0; row < ROWS; row++) {
      const phase = row * 0.8 + col * 0.4; // wave flows down the wall
      const size = PANEL * 0.4 * (1 + sin(frameCount * 0.05 + phase));
      circle(col * PANEL + PANEL / 2, row * PANEL + PANEL / 2, size);
    }
  }

  // faint panel grid - delete these 3 lines for the real show
  stroke(255, 40);
  noFill();
  for (let c = 1; c < COLS; c++) line(c * PANEL, 0, c * PANEL, height);
  for (let r = 1; r < ROWS; r++) line(0, r * PANEL, width, r * PANEL);
}
