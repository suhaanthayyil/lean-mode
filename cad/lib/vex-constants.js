/**
 * vex-constants.js — VEX V5 (EDR) dimensional standard.
 *
 * BASE UNIT FOR THIS WHOLE CAD PROJECT IS THE INCH.
 * VEX is an imperial system (0.5" hole pitch, 24 diametral-pitch gears,
 * #25 chain at 0.25" pitch), so modelling in inches keeps every number a
 * round, checkable figure instead of a 12.7000001 rounding swamp.
 * Use MM to convert for export/display.
 */

export const MM = 25.4;            // multiply inches -> millimetres
export const inches = (v) => v;    // documentation helper
export const mm = (v) => v / MM;   // millimetres -> inches

/* ----------------------------------------------------------------- *
 * STRUCTURE
 * ----------------------------------------------------------------- */

/** Hole pitch of every VEX structural part. */
export const PITCH = 0.5;
/** Hole diameter (clears an 8-32 screw). */
export const HOLE_D = 0.181;
export const HOLE_R = HOLE_D / 2;
/** Sheet thickness of aluminium structural stock. */
export const SHEET = 0.049;
/** First hole is half a pitch in from the end of a part. */
export const EDGE = PITCH / 2;
/** Outside corner break on formed parts. */
export const CORNER_R = 0.06;

/** Length in inches of a part that is `n` holes long. */
export const holes = (n) => n * PITCH;

/* ----------------------------------------------------------------- *
 * SHAFTS / MOTION
 * ----------------------------------------------------------------- */

/** Low-strength square shaft, across flats. */
export const SHAFT_LS = 0.125;
/** High-strength square shaft, across flats. */
export const SHAFT_HS = 0.25;

/** Gears are 24 diametral pitch: pitch diameter = teeth / 24. */
export const DP = 24;
export const gearPD = (teeth) => teeth / DP;
export const gearOD = (teeth) => (teeth + 2) / DP;
/** Centre distance for two meshing DP24 gears. */
export const meshDistance = (t1, t2) => (t1 + t2) / (2 * DP);

/** Face width of a high-strength gear / of a low-strength gear. */
export const GEAR_T_HS = 0.25;
export const GEAR_T_LS = 0.125;

/** #25 roller chain. */
export const CHAIN_PITCH = 0.25;
export const CHAIN_ROLLER_D = 0.130;
export const CHAIN_ROLLER_W = 0.125;
export const CHAIN_PLATE_H = 0.170;
export const CHAIN_PLATE_T = 0.030;
export const CHAIN_WIDTH = 0.195;          // outside of plate to outside of plate
/** Pitch diameter of an N-tooth #25 sprocket. */
export const sprocketPD = (teeth) => CHAIN_PITCH / Math.sin(Math.PI / teeth);

/* ----------------------------------------------------------------- *
 * WHEELS
 * ----------------------------------------------------------------- */

export const WHEEL = {
  omni4:    { od: 4.000, width: 0.960, hubOd: 2.30, rollers: 9,  rows: 2 },
  omni325:  { od: 3.250, width: 0.960, hubOd: 1.85, rollers: 8,  rows: 2 },
  traction4:{ od: 4.000, width: 0.500, hubOd: 2.30 },
  flex2:    { od: 2.000, width: 0.500 },
};

/* ----------------------------------------------------------------- *
 * V5 ELECTRONICS  (envelope dimensions, outside of case)
 * ----------------------------------------------------------------- */

export const V5 = {
  motor:   { l: 2.24, w: 1.87, h: 1.42, shaftBossD: 0.98, shaftBossH: 0.30 },
  brain:   { l: 4.45, w: 3.43, h: 1.02, screenW: 2.55, screenH: 1.46 },
  battery: { l: 3.62, w: 2.24, h: 0.87 },
  radio:   { l: 1.61, w: 1.02, h: 0.40 },
};

/** V5 motor gear cartridges: colour and output RPM. */
export const CARTRIDGE = {
  red:   { rpm: 100, color: 0xd02030 },
  green: { rpm: 200, color: 0x2fae5a },
  blue:  { rpm: 600, color: 0x2f6fd0 },
};

/* ----------------------------------------------------------------- *
 * FASTENERS
 * ----------------------------------------------------------------- */

export const SCREW = { headD: 0.290, headH: 0.075, shankD: 0.164 };
export const NUT   = { af: 0.344, h: 0.110 };           // 8-32 nylock, across flats
export const STANDOFF = { af: 0.440 };                   // hex standoff across flats

/* ----------------------------------------------------------------- *
 * COMPETITION ENVELOPE
 * ----------------------------------------------------------------- */

/** V5RC starting-size cube (R4: 18 x 18 x 18 inches). */
export const SIZE_LIMIT = 18.0;

/* ----------------------------------------------------------------- *
 * APPEARANCE
 * ----------------------------------------------------------------- */

export const COLOR = {
  aluminum:  0xb6bcc4,
  steel:     0x8f949b,
  vexRed:    0xc8102e,
  vexRedLit: 0xe03048,
  black:     0x24272c,
  darkGray:  0x3a3f46,
  rubber:    0x1c1e22,
  rollerGray:0xd8dce1,
  screen:    0x1b2b3a,
  brass:     0xb08d4a,
  chain:     0x6e747c,
};
