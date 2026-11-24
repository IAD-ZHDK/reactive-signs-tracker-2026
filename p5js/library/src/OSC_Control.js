const OSC = require('osc-js');

const DEFAULT_OPTIONS = {
  address: '/position',
  host: 'localhost',
  port: 8025,
  retryInterval: 2000,
  signalTimeout: 2000,
  resize: true,
};

const osc = new OSC();
let opened = false;
let connectionOptions = DEFAULT_OPTIONS;
let reconnectInterval;
let fallbackInterval;
let listeningToMouse = false;
let pointer = null;
let canvasObserver;
let canvasAspectRatio;
const positionAddresses = new Set();

export const posNormal = { x: 0.5, y: 0.5, z: 0 };
export const position = { x: 0, y: 0, z: 0 };
export let x = posNormal.x;
export let y = posNormal.y;
export let z = posNormal.z;
export let connected = false;
export let oscSignal = false;
export let lastOSC = 0;

function numberOrUndefined(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function updatePosition(nextX, nextY, nextZ) {
  if (nextX !== undefined) {
    posNormal.x = x = nextX;
  }
  if (nextY !== undefined) {
    posNormal.y = y = nextY;
  }
  if (nextZ !== undefined) {
    posNormal.z = z = nextZ;
  }

  const { logicalWidth, logicalHeight } = canvasSize();
  position.x = posNormal.x * logicalWidth;
  position.y = posNormal.y * logicalHeight;
  position.z = posNormal.z;
  lastOSC = performance.now();
  oscSignal = true;
}

function canvasSize() {
  const canvas = document.querySelector('canvas');
  const rect = canvas?.getBoundingClientRect();
  const logicalWidth = Number.isFinite(window.width) && window.width > 0
    ? window.width
    : canvas?.width || window.innerWidth;
  const logicalHeight = Number.isFinite(window.height) && window.height > 0
    ? window.height
    : canvas?.height || window.innerHeight;

  return {
    left: rect?.left || 0,
    top: rect?.top || 0,
    width: rect?.width || logicalWidth,
    height: rect?.height || logicalHeight,
    logicalWidth,
    logicalHeight,
  };
}

function resizeCanvasToOriginalRatio() {
  const canvas = document.querySelector('canvas');
  if (!canvas) return;

  if (!canvasAspectRatio) {
    const { logicalWidth, logicalHeight } = canvasSize();
    canvasAspectRatio = logicalWidth / logicalHeight;
  }

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let targetWidth = viewportWidth;
  let targetHeight = targetWidth / canvasAspectRatio;

  if (targetHeight > viewportHeight) {
    targetHeight = viewportHeight;
    targetWidth = targetHeight * canvasAspectRatio;
  }

  targetWidth = Math.max(1, Math.floor(targetWidth));
  targetHeight = Math.max(1, Math.floor(targetHeight));

  if (typeof window.resizeCanvas === 'function') {
    window.resizeCanvas(targetWidth, targetHeight, true);
    canvas.style.width = `${targetWidth}px`;
    canvas.style.height = `${targetHeight}px`;
  } else {
    canvas.style.width = `${targetWidth}px`;
    canvas.style.height = `${targetHeight}px`;
  }

  syncMouseFallback();
}

function watchForCanvas() {
  if (document.querySelector('canvas')) {
    resizeCanvasToOriginalRatio();
    return;
  }

  canvasObserver = new MutationObserver(() => {
    if (!document.querySelector('canvas')) return;
    canvasObserver.disconnect();
    canvasObserver = undefined;
    resizeCanvasToOriginalRatio();
  });
  canvasObserver.observe(document.body, { childList: true, subtree: true });
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
  pointer = {
    clientX: event.clientX,
    clientY: event.clientY,
  };
  syncMouseFallback();
}

function syncMouseFallback() {
  if (!pointer || hasOSCSignal(connectionOptions.signalTimeout)) return;

  const { left, top, width, height, logicalWidth, logicalHeight } = canvasSize();

  position.x = (pointer.clientX - left) * (logicalWidth / width);
  position.y = (pointer.clientY - top) * (logicalHeight / height);
  posNormal.x = Math.max(0, Math.min(1, position.x / logicalWidth));
  posNormal.y = Math.max(0, Math.min(1, position.y / logicalHeight));
  posNormal.z = 0;

  x = posNormal.x;
  y = posNormal.y;
  z = 0;
  position.z = 0;
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

  if (config.resize) {
    window.addEventListener('resize', resizeCanvasToOriginalRatio);
    document.addEventListener('fullscreenchange', resizeCanvasToOriginalRatio);
    watchForCanvas();
  }

  osc.open({ host: config.host, port: config.port });
  reconnectInterval = window.setInterval(reconnect, config.retryInterval);
  fallbackInterval = window.setInterval(syncMouseFallback, 50);
}

export function resizeToOriginalRatio() {
  if (!connectionOptions.resize) return;
  resizeCanvasToOriginalRatio();
}

export function closeOSC() {
  if (!opened) return;
  osc.close();
  opened = false;
  connected = false;
  window.clearInterval(reconnectInterval);
  window.clearInterval(fallbackInterval);
  window.removeEventListener('pointermove', updateFromMouse);
  window.removeEventListener('resize', resizeCanvasToOriginalRatio);
  document.removeEventListener('fullscreenchange', resizeCanvasToOriginalRatio);
  canvasObserver?.disconnect();
  canvasObserver = undefined;
  listeningToMouse = false;
  pointer = null;
}

export function hasOSCSignal(maxAge = 2000) {
  if (lastOSC === 0) {
    oscSignal = false;
  } else {
    oscSignal = performance.now() - lastOSC <= maxAge;
  }
  return oscSignal;
}
