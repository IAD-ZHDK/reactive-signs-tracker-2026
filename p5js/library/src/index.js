import { setUpOSC } from './OSC_Control.js';

export {
  closeOSC,
  connected,
  hasOSCSignal,
  lastOSC,
  oscSignal,
  position,
  posNormal,
  setUpOSC,
  x,
  y,
  z,
} from './OSC_Control.js';

// Keep the public setup function small enough to call from a p5.js setup().
export function setup(options) {
  setUpOSC(options);
}
