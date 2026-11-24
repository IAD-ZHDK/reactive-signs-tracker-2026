// LED wall: 2 columns x 6 rows, each panel 240 x 240 px
const PANEL = 240;
const COLS = 2;
const ROWS = 6;
const AUTO_RESIZE = true;

function setup() {
  createCanvas(COLS * PANEL, ROWS * PANEL);
  poster.setup({ resize: AUTO_RESIZE }); // setup poster with auto resize option
  rectMode(CENTER);
}

function draw() {
  const { x, y, z } = poster.position;
  const depth = constrain(z, 0, 1);
  const flowY = poster.posNormal.y;

  background(0);
  noStroke();

  push();
  translate(width / 2, height / 2);
  const totalSteps = 25;
  const step = height / totalSteps;

  for (let i = totalSteps; i > 0; i--) {
    const wave = sin(frameCount * 0.025 + i * 0.35 + flowY * TWO_PI);
    const brightness = map(wave, -1, 1, 25, 255);
    fill(brightness);
    rotate(radians(i + x * 0.01 + wave * 3 * depth));
    rect(0, flowY * height * 0.2 - height * 0.1, i * step, i * step);
  }
  pop();

  const pulse = 1 + sin(frameCount * 0.08 + y * 0.02) * 0.25;
  noFill();
  stroke(255, 80 + depth * 140);
  strokeWeight(2 + depth * 8);
  circle(x, y, (35 + depth * 120) * pulse);

  fill(255, 180 + depth * 75);
  noStroke();
  circle(x, y, 6 + depth * 36);
}
