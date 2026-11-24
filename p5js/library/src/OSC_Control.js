const OSC = require('osc-js');

const DEFAULT_OPTIONS = {
  address: '/position',
  host: 'localhost',
  port: 8025,
  retryInterval: 2000,
  signalTimeout: 2000,
};

const osc = new OSC();
let opened = false;
let connectionOptions = DEFAULT_OPTIONS;
let reconnectInterval;
let listeningToMouse = false;
const positionAddresses = new Set();

export const position = { x: 0.5, y: 0.5, z: 0 };
export const posNormal = position;
export let x = position.x;
export let y = position.y;
export let z = position.z;
export let connected = false;
export let oscSignal = false;
export let lastOSC = 0;

function numberOrUndefined(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function updatePosition(nextX, nextY, nextZ) {
  if (nextX !== undefined) {
    position.x = x = nextX;
  }
  if (nextY !== undefined) {
    position.y = y = nextY;
  }
  if (nextZ !== undefined) {
    position.z = z = nextZ;
  }

  lastOSC = performance.now();
  oscSignal = true;
}

function readPosition(message) {
  const args = message.args || [];
  const nextX = numberOrUndefined(args[0]);
  const nextY = numberOrUndefined(args[1]);
  const nextZ = numberOrUndefined(args[2]);

  if (nextX !== undefined && nextY !== undefined) {
    updatePosition(nextX, nextY, nextZ);
  }
}

function readLegacyDepth(message) {
  const args = message.args || [];
  const nextX = numberOrUndefined(args[3]);
  const nextY = numberOrUndefined(args[4]);
  const nextZ = numberOrUndefined(args[5]);

  if (nextX !== undefined && nextY !== undefined) {
    updatePosition(nextX, nextY, nextZ);
  }
}

function readAxis(axis, message) {
  const value = numberOrUndefined(message.args?.[0]);
  if (value === undefined) return;

  updatePosition(
    axis === 'x' ? value : undefined,
    axis === 'y' ? value : undefined,
    axis === 'z' ? value : undefined,
  );
}

function updateFromMouse(event) {
  if (hasOSCSignal(connectionOptions.signalTimeout)) return;

  position.x = x = Math.max(0, Math.min(1, event.clientX / window.innerWidth));
  position.y = y = Math.max(0, Math.min(1, event.clientY / window.innerHeight));
  position.z = z = 0;
}

function reconnect() {
  if (!opened || connected || osc.status() !== OSC.STATUS.IS_CLOSED) return;

  osc.open({
    host: connectionOptions.host,
    port: connectionOptions.port,
  });
}

osc.on('open', () => {
  connected = true;
  console.info(`OSC connected at ws://${connectionOptions.host}:${connectionOptions.port}`);
});

osc.on('close', () => {
  connected = false;
});

osc.on('error', (error) => {
  console.error('OSC connection failed.', error);
});

osc.on('/x', (message) => readAxis('x', message));
osc.on('/y', (message) => readAxis('y', message));
osc.on('/z', (message) => readAxis('z', message));
osc.on('/depth', readLegacyDepth);

export function setUpOSC(options = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };

  if (opened) return;
  opened = true;
  connectionOptions = config;

  if (!positionAddresses.has(config.address)) {
    osc.on(config.address, readPosition);
    positionAddresses.add(config.address);
  }

  if (!listeningToMouse) {
    window.addEventListener('pointermove', updateFromMouse);
    listeningToMouse = true;
  }

  osc.open({ host: config.host, port: config.port });
  reconnectInterval = window.setInterval(reconnect, config.retryInterval);
}

export function closeOSC() {
  if (!opened) return;
  osc.close();
  opened = false;
  connected = false;
  window.clearInterval(reconnectInterval);
  window.removeEventListener('pointermove', updateFromMouse);
  listeningToMouse = false;
}

export function hasOSCSignal(maxAge = 2000) {
  if (lastOSC === 0) {
    oscSignal = false;
  } else {
    oscSignal = performance.now() - lastOSC <= maxAge;
  }
  return oscSignal;
}
