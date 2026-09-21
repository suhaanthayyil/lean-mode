/**
 * vex-parts.js — parametric geometry factories for VEX V5 parts.
 *
 * Every factory returns a THREE.BufferGeometry in INCHES, built from the
 * real VEX dimensional standard in ./vex-constants.js. Holes are genuinely
 * cut through the material (extruded shapes with hole paths), gear and
 * sprocket teeth are generated from the DP24 / #25 definitions rather than
 * being drawn as decoration.
 *
 * Geometry is cached by parameter signature, so a robot with 24 identical
 * C-channels builds one channel and instances it.
 */

import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import * as C from './vex-constants.js';

/* ================================================================= *
 * cache
 * ================================================================= */

const _cache = new Map();
function cached(key, build) {
  let g = _cache.get(key);
  if (!g) {
    g = build();
    if (g && g.isBufferGeometry) g.userData.cacheKey = key;
    _cache.set(key, g);
  }
  return g;
}
export function cacheStats() { return { geometries: _cache.size }; }

/* ================================================================= *
 * low-level helpers
 * ================================================================= */


/**
 * Merge a list of geometries that may mix indexed primitives (Cylinder,
 * Box, Torus) with non-indexed ones (Extrude, Lathe). three's
 * mergeGeometries refuses mismatched attribute sets, so normalise first.
 */
function merge(list) {
  const flat = list.filter(Boolean).map((g) => (g.index ? g.toNonIndexed() : g));
  const KEEP = ['position', 'normal', 'uv'];
  for (const g of flat) {
    for (const k of Object.keys(g.attributes)) if (!KEEP.includes(k)) g.deleteAttribute(k);
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!g.attributes.uv) {
      g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    }
  }
  const out = mergeGeometries(flat, false);
  if (!out) throw new Error('vex-parts: geometry merge failed');
  out.clearGroups();
  return out;
}

/** Rounded rectangle centred on the origin, as a THREE.Shape. */
function roundedRect(w, h, r = C.CORNER_R) {
  r = Math.min(r, w / 2, h / 2);
  const s = new THREE.Shape();
  const x = w / 2, y = h / 2;
  s.moveTo(-x + r, -y);
  s.lineTo(x - r, -y);
  s.absarc(x - r, -y + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x, y - r);
  s.absarc(x - r, y - r, r, 0, Math.PI / 2, false);
  s.lineTo(-x + r, y);
  s.absarc(-x + r, y - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(-x, -y + r);
  s.absarc(-x + r, -y + r, r, Math.PI, 1.5 * Math.PI, false);
  return s;
}

/** Punch circular holes into a shape. */
function punch(shape, pts, r = C.HOLE_R) {
  for (const [hx, hy] of pts) {
    const p = new THREE.Path();
    p.absarc(hx, hy, r, 0, Math.PI * 2, true);
    shape.holes.push(p);
  }
  return shape;
}

/**
 * A flat panel of material: spans X = [-w/2, w/2], Y = [-h/2, h/2],
 * Z = [-t/2, t/2], with `holePts` cut through the thickness.
 */
function panel(w, h, t, holePts = [], cornerR = C.CORNER_R) {
  const shape = punch(roundedRect(w, h, cornerR), holePts);
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: t, bevelEnabled: false, curveSegments: 10,
  });
  g.translate(0, 0, -t / 2);
  return g;
}

/** Evenly spaced hole centres along an axis for an `n`-hole run of length n*PITCH. */
export function holeRow(n) {
  const L = n * C.PITCH;
  return Array.from({ length: n }, (_, i) => -L / 2 + C.EDGE + i * C.PITCH);
}

/** Full grid of hole centres for an n x m hole panel. */
function holeGrid(n, m) {
  const xs = holeRow(n), ys = holeRow(m);
  const out = [];
  for (const y of ys) for (const x of xs) out.push([x, y]);
  return out;
}

/* ================================================================= *
 * STRUCTURE
 * ================================================================= */

/**
 * C-channel.  `len` holes long, web `web` holes wide, flanges `flange`
 * holes tall (VEX 1xNx1 stock).
 *
 * Local frame: length along +X, web lies in the XY plane with its TOP
 * surface at z = 0, flanges rise in +Z at y = +/- webWidth/2.
 * Origin is the centre of the part.
 */
export function cChannel(len, web = 2, flange = 1) {
  return cached(`cc:${len}:${web}:${flange}`, () => {
    const L = C.holes(len), W = C.holes(web), F = C.holes(flange), t = C.SHEET;
    const parts = [];

    // web
    const webG = panel(L, W, t, holeGrid(len, web));
    webG.translate(0, 0, -t / 2);
    parts.push(webG);

    // flanges: built flat, rotated up, holes land at z = 0.25, 0.75, ...
    for (const sign of [-1, 1]) {
      const f = panel(L, F, t, holeGrid(len, flange));
      f.rotateX(Math.PI / 2);
      f.translate(0, sign * (W / 2 - t / 2), F / 2);
      parts.push(f);
    }
    return merge(parts);
  });
}

/**
 * Angle / L-bracket stock. Length along +X, one leg in the XY plane
 * (top surface z = 0) extending in +Y, the other rising in +Z at y = 0.
 */
export function angleBar(len, legA = 1, legB = 1) {
  return cached(`ang:${len}:${legA}:${legB}`, () => {
    const L = C.holes(len), A = C.holes(legA), B = C.holes(legB), t = C.SHEET;
    const flat = panel(L, A, t, holeGrid(len, legA));
    flat.translate(0, A / 2, -t / 2);
    const up = panel(L, B, t, holeGrid(len, legB));
    up.rotateX(Math.PI / 2);
    up.translate(0, t / 2, B / 2);
    return merge([flat, up]);
  });
}

/** Flat bar / plate, `len` x `wid` holes. Lies in XY, centred, thickness in Z. */
export function flatBar(len, wid = 1) {
  return cached(`flat:${len}:${wid}`, () =>
    panel(C.holes(len), C.holes(wid), C.SHEET, holeGrid(len, wid)));
}

/** Hex standoff of the given length, axis along +Z, centred. */
export function standoff(length) {
  return cached(`so:${length.toFixed(3)}`, () => {
    const r = C.STANDOFF.af / 2 / Math.cos(Math.PI / 6);
    const g = new THREE.CylinderGeometry(r, r, length, 6, 1);
    g.rotateX(Math.PI / 2);
    return g;
  });
}

/** 8-32 screw: head at z = 0, shank running in -Z. */
export function screw(length = 0.375) {
  return cached(`scr:${length.toFixed(3)}`, () => {
    // head sits on the material at z = 0 and rises in +Z; shank runs into -Z
    const head = new THREE.CylinderGeometry(C.SCREW.headD / 2, C.SCREW.headD / 2 * 0.90, C.SCREW.headH, 14);
    head.rotateX(Math.PI / 2);
    head.translate(0, 0, C.SCREW.headH / 2);
    const shank = new THREE.CylinderGeometry(C.SCREW.shankD / 2, C.SCREW.shankD / 2, length, 10);
    shank.rotateX(Math.PI / 2);
    shank.translate(0, 0, -length / 2);
    return merge([head, shank]);
  });
}

/** 8-32 nylock nut, axis along +Z. */
export function nut() {
  return cached('nut', () => {
    const r = C.NUT.af / 2 / Math.cos(Math.PI / 6);
    const g = new THREE.CylinderGeometry(r, r, C.NUT.h, 6, 1);
    g.rotateX(Math.PI / 2);
    return g;
  });
}

/* ================================================================= *
 * SHAFTS
 * ================================================================= */

/** Square shaft along +X, centred. `hs` selects 1/4" high-strength stock. */
export function shaft(length, hs = false) {
  return cached(`sh:${length.toFixed(3)}:${hs}`, () => {
    const a = hs ? C.SHAFT_HS : C.SHAFT_LS;
    const g = new THREE.BoxGeometry(length, a, a);
    return g;
  });
}

/** Shaft collar, axis along +X. */
export function collar(hs = false) {
  return cached(`col:${hs}`, () => {
    const od = hs ? 0.50 : 0.375, w = hs ? 0.20 : 0.155;
    const g = new THREE.CylinderGeometry(od / 2, od / 2, w, 18);
    g.rotateZ(Math.PI / 2);
    return g;
  });
}

/** Bearing flat (the white nylon block), lying in XY, thickness in Z. */
export function bearingFlat() {
  return cached('brg', () => {
    const shape = roundedRect(C.holes(2), C.holes(2), 0.16);
    punch(shape, [[-C.PITCH / 2, C.PITCH / 2], [C.PITCH / 2, -C.PITCH / 2]]);
    const p = new THREE.Path(); p.absarc(0, 0, 0.19, 0, Math.PI * 2, true);
    shape.holes.push(p);
    const g = new THREE.ExtrudeGeometry(shape, { depth: 0.115, bevelEnabled: false, curveSegments: 12 });
    g.translate(0, 0, -0.0575);
    return g;
  });
}

/* ================================================================= *
 * GEARS — DP24 involute-style tooth profile
 * ================================================================= */

/**
 * Spur gear, axis along +X (so it sits on a shaft running along X),
 * centred on the origin.
 *
 * @param {number} teeth
 * @param {boolean} hs  high-strength (0.25" face, 1/4" square bore)
 */
export function gear(teeth, hs = true) {
  return cached(`gear:${teeth}:${hs}`, () => {
    const pr = C.gearPD(teeth) / 2;
    const addendum = 1 / C.DP;
    const dedendum = 1.25 / C.DP;
    const rTip = pr + addendum;
    const rRoot = Math.max(0.08, pr - dedendum);
    const step = (Math.PI * 2) / teeth;

    // tooth half-widths, in radians, at root / pitch / tip circles
    const hRoot = step * 0.30, hPitch = step * 0.25, hTip = step * 0.155;

    const pts = [];
    const at = (r, a) => pts.push(new THREE.Vector2(r * Math.cos(a), r * Math.sin(a)));
    for (let i = 0; i < teeth; i++) {
      const a = i * step;
      at(rRoot, a - hRoot);
      at(pr - dedendum * 0.35, a - hPitch * 1.08);
      at(pr, a - hPitch);
      at(rTip - addendum * 0.35, a - hTip * 1.25);
      at(rTip, a - hTip);
      at(rTip, a + hTip);
      at(rTip - addendum * 0.35, a + hTip * 1.25);
      at(pr, a + hPitch);
      at(pr - dedendum * 0.35, a + hPitch * 1.08);
      at(rRoot, a + hRoot);
      // root fillet arc through to the next tooth
      const gapA = a + hRoot, gapB = a + step - hRoot;
      const segs = 4;
      for (let k = 1; k < segs; k++) at(rRoot, gapA + (gapB - gapA) * k / segs);
    }

    const shape = new THREE.Shape(pts);

    // square bore
    const bore = hs ? C.SHAFT_HS : C.SHAFT_LS;
    const b = bore / 2 + 0.006;
    const boreP = new THREE.Path();
    boreP.moveTo(-b, -b); boreP.lineTo(b, -b); boreP.lineTo(b, b); boreP.lineTo(-b, b); boreP.closePath();
    shape.holes.push(boreP);

    // lightening pockets + the ring of screw holes VEX puts in large gears
    if (teeth >= 36) {
      const spokes = teeth >= 60 ? 6 : 5;
      const rPocket = rRoot * 0.60;
      const pocketR = rRoot * 0.24;
      for (let i = 0; i < spokes; i++) {
        const a = (i / spokes) * Math.PI * 2 + step / 2;
        const p = new THREE.Path();
        p.absarc(rPocket * Math.cos(a), rPocket * Math.sin(a), pocketR, 0, Math.PI * 2, true);
        shape.holes.push(p);
      }
    }
    if (teeth >= 24) {
      // 4 mounting holes on a 0.5" square bolt circle (VEX standard)
      for (const [sx, sy] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) {
        const p = new THREE.Path();
        p.absarc(sx * C.PITCH / 2, sy * C.PITCH / 2, C.HOLE_R, 0, Math.PI * 2, true);
        shape.holes.push(p);
      }
    }

    const t = hs ? C.GEAR_T_HS : C.GEAR_T_LS;
    const g = new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false, curveSegments: 8 });
    g.translate(0, 0, -t / 2);
    g.rotateY(Math.PI / 2);          // face normal -> X
    return g;
  });
}

/* ================================================================= *
 * SPROCKETS — #25 chain
 * ================================================================= */

/** #25 sprocket, axis along +X, centred. */
export function sprocket(teeth, hs = true) {
  return cached(`spk:${teeth}:${hs}`, () => {
    const pr = C.sprocketPD(teeth) / 2;
    const rr = C.CHAIN_ROLLER_D / 2 + 0.008;     // roller seat radius + clearance
    const rTip = pr + 0.085;
    const step = (Math.PI * 2) / teeth;

    const pts = [];
    const at = (x, y) => pts.push(new THREE.Vector2(x, y));
    for (let i = 0; i < teeth; i++) {
      const th = i * step;
      const cx = pr * Math.cos(th), cy = pr * Math.sin(th);
      // roller seat: sweep the seat circle from the entering to the exiting side
      const segs = 7;
      for (let k = 0; k <= segs; k++) {
        const psi = th + Math.PI * (240 - (240 - 120) * (k / segs)) / 180;
        at(cx + rr * Math.cos(psi), cy + rr * Math.sin(psi));
      }
      // tooth tip, midway to the next seat
      const tipA = th + step / 2;
      at((rTip - 0.02) * Math.cos(tipA - step * 0.12), (rTip - 0.02) * Math.sin(tipA - step * 0.12));
      at(rTip * Math.cos(tipA), rTip * Math.sin(tipA));
      at((rTip - 0.02) * Math.cos(tipA + step * 0.12), (rTip - 0.02) * Math.sin(tipA + step * 0.12));
    }

    const shape = new THREE.Shape(pts);
    const bore = hs ? C.SHAFT_HS : C.SHAFT_LS;
    const b = bore / 2 + 0.006;
    const boreP = new THREE.Path();
    boreP.moveTo(-b, -b); boreP.lineTo(b, -b); boreP.lineTo(b, b); boreP.lineTo(-b, b); boreP.closePath();
    shape.holes.push(boreP);

    for (const [sx, sy] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) {
      const p = new THREE.Path();
      p.absarc(sx * C.PITCH / 2, sy * C.PITCH / 2, C.HOLE_R, 0, Math.PI * 2, true);
      shape.holes.push(p);
    }
    if (teeth >= 24) {
      const spokes = 6, rPocket = pr * 0.58, pocketR = pr * 0.20;
      for (let i = 0; i < spokes; i++) {
        const a = (i / spokes) * Math.PI * 2 + step / 2;
        const p = new THREE.Path();
        p.absarc(rPocket * Math.cos(a), rPocket * Math.sin(a), pocketR, 0, Math.PI * 2, true);
        shape.holes.push(p);
      }
    }

    const t = hs ? 0.150 : 0.100;
    const g = new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false, curveSegments: 8 });
    g.translate(0, 0, -t / 2);
    g.rotateY(Math.PI / 2);
    return g;
  });
}

/* ================================================================= *
 * #25 CHAIN — a real link-by-link run around two sprockets
 * ================================================================= */

/**
 * Build a closed #25 chain loop around two sprockets.
 *
 * The chain lives in the world YZ plane with its axis along X, matching
 * gear()/sprocket() which are rotated so their axis is +X.
 *
 * @param {{y:number,z:number,teeth:number}} A first sprocket
 * @param {{y:number,z:number,teeth:number}} B second sprocket
 * @returns {{geometry: THREE.BufferGeometry, links: number,
 *            phaseA: number, phaseB: number, pitchUsed: number}}
 *          phaseA/phaseB are the rotation.x values that make each
 *          sprocket's tooth seats line up with the chain rollers.
 */
export function chainLoop(A, B) {
  const r1 = C.sprocketPD(A.teeth) / 2;
  const r2 = C.sprocketPD(B.teeth) / 2;
  const dy = B.y - A.y, dz = B.z - A.z;
  const L = Math.hypot(dy, dz);
  if (L <= Math.abs(r1 - r2)) throw new Error('chainLoop: sprockets too close');
  const a = Math.atan2(dz, dy);
  const phi = Math.acos((r1 - r2) / L);

  const norm = (t) => ((t % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const ptOn = (c, r, ang) => [c.y + r * Math.cos(ang), c.z + r * Math.sin(ang)];

  // Counter-clockwise loop:
  //   wrap A over its far side, tangent across to B, wrap B, tangent back.
  const aOut = a - phi;                 // leaves A here
  const aIn  = a + phi;                 // returns to A here
  const wrapA = norm(aIn - aOut);       // going CCW from aOut? no: A wraps aIn -> aOut+2pi
  const arcA = norm(aOut - aIn);        // CCW sweep on A (far side)
  const arcB = norm(aIn - aOut);        // CCW sweep on B (far side)

  const P_A_out = ptOn(A, r1, aOut);
  const P_B_out = ptOn(B, r2, aOut);
  const P_B_in  = ptOn(B, r2, aIn);
  const P_A_in  = ptOn(A, r1, aIn);

  const tanLen = Math.hypot(P_B_out[0] - P_A_out[0], P_B_out[1] - P_A_out[1]);
  const total = tanLen * 2 + arcA * r1 + arcB * r2;

  // The chain must close on a whole EVEN number of links (#25 alternates
  // inner and outer link plates), so round to even and nudge the pitch to suit.
  let links = Math.max(8, Math.round(total / C.CHAIN_PITCH));
  if (links % 2) links += 1;
  const pitchUsed = total / links;

  /** Walk distance s around the loop -> {y, z, dir}. */
  function at(s) {
    s = ((s % total) + total) % total;
    // 1. tangent A_out -> B_out
    if (s < tanLen) {
      const u = s / tanLen;
      return {
        y: P_A_out[0] + (P_B_out[0] - P_A_out[0]) * u,
        z: P_A_out[1] + (P_B_out[1] - P_A_out[1]) * u,
        dir: Math.atan2(P_B_out[1] - P_A_out[1], P_B_out[0] - P_A_out[0]),
        on: null,
      };
    }
    s -= tanLen;
    // 2. wrap B (CCW from aOut to aIn)
    if (s < arcB * r2) {
      const ang = aOut + s / r2;
      return { y: B.y + r2 * Math.cos(ang), z: B.z + r2 * Math.sin(ang), dir: ang + Math.PI / 2, on: 'B', ang };
    }
    s -= arcB * r2;
    // 3. tangent B_in -> A_in
    if (s < tanLen) {
      const u = s / tanLen;
      return {
        y: P_B_in[0] + (P_A_in[0] - P_B_in[0]) * u,
        z: P_B_in[1] + (P_A_in[1] - P_B_in[1]) * u,
        dir: Math.atan2(P_A_in[1] - P_B_in[1], P_A_in[0] - P_B_in[0]),
        on: null,
      };
    }
    s -= tanLen;
    // 4. wrap A (CCW from aIn to aOut)
    const ang = aIn + s / r1;
    return { y: A.y + r1 * Math.cos(ang), z: A.z + r1 * Math.sin(ang), dir: ang + Math.PI / 2, on: 'A', ang };
  }

  // --- link geometry, built once and stamped along the path ---------
  const rollerG = new THREE.CylinderGeometry(
    C.CHAIN_ROLLER_D / 2, C.CHAIN_ROLLER_D / 2, C.CHAIN_ROLLER_W, 10);
  rollerG.rotateZ(Math.PI / 2);   // axis -> X

  const plateShape = roundedRect(pitchUsed + C.CHAIN_PLATE_H * 0.9, C.CHAIN_PLATE_H, C.CHAIN_PLATE_H / 2);
  const plateG = new THREE.ExtrudeGeometry(plateShape, { depth: C.CHAIN_PLATE_T, bevelEnabled: false, curveSegments: 6 });
  plateG.translate(0, 0, -C.CHAIN_PLATE_T / 2);
  plateG.rotateY(Math.PI / 2);    // plate face normal -> X, length -> -Z, height -> Y

  const parts = [];
  const rollers = [];
  const plateOff = (C.CHAIN_WIDTH - C.CHAIN_PLATE_T) / 2;

  for (let i = 0; i < links; i++) {
    const s = i * pitchUsed;
    const p = at(s);
    rollers.push(p);

    const roll = rollerG.clone();
    roll.translate(0, p.y, p.z);
    parts.push(roll);

    // side plates bridge roller i -> roller i+1
    const q = at(s + pitchUsed);
    const my = (p.y + q.y) / 2, mz = (p.z + q.z) / 2;
    const ang = Math.atan2(q.z - p.z, q.y - p.y);
    for (const sign of [-1, 1]) {
      const pl = plateG.clone();
      // plate local: length along -Z, height along Y -> spin into the link direction
      pl.rotateX(0);
      const m = new THREE.Matrix4().makeRotationX(ang + Math.PI / 2);
      pl.applyMatrix4(m);
      pl.translate(sign * plateOff * (i % 2 ? 1.0 : 0.62), my, mz);
      parts.push(pl);
    }
  }

  const geometry = merge(parts);

  // Phase each sprocket so its seats sit under the rollers that wrap it.
  const seatPhase = (sp, teeth) => {
    const hit = rollers.find((r) => r.on === sp);
    if (!hit) return 0;
    const step = (Math.PI * 2) / teeth;
    const want = hit.ang + Math.PI / 2;          // shape-space angle of that seat
    return -(((want % step) + step) % step);
  };

  return {
    geometry,
    links,
    pitchUsed,
    lengthIn: total,
    phaseA: seatPhase('A', A.teeth),
    phaseB: seatPhase('B', B.teeth),
    rollers,
    at,
  };
}

/* ================================================================= *
 * WHEELS  (axis along +X)
 * ================================================================= */

function barrelRoller(len, rMax) {
  const pts = [];
  const N = 8;
  for (let i = 0; i <= N; i++) {
    const u = i / N;
    const y = -len / 2 + len * u;
    const r = rMax * (0.55 + 0.45 * Math.cos((u - 0.5) * Math.PI * 0.92));
    pts.push(new THREE.Vector2(Math.max(0.02, r), y));
  }
  return new THREE.LatheGeometry(pts, 12);
}

/** VEX omni wheel. Returns {hub, rollers} geometries so they can be coloured apart. */
export function omniWheel(kind = 'omni4') {
  return cached(`omni:${kind}`, () => {
    const s = C.WHEEL[kind];
    const rollerLen = s.width * 0.225;   // two rows must fit inside the hub width
    const rollerR = (s.od - s.hubOd) / 2 * 0.98;
    const ringR = s.od / 2 - rollerR;

    const parts = [];
    // central hub disc with the VEX square bore boss
    const disc = new THREE.CylinderGeometry(ringR * 0.97, ringR * 0.97, s.width * 0.30, 28);
    disc.rotateZ(Math.PI / 2);
    parts.push(disc);
    const boss = new THREE.CylinderGeometry(0.42, 0.42, s.width, 20);
    boss.rotateZ(Math.PI / 2);
    parts.push(boss);
    // two spoked side rings that carry the rollers
    for (const sign of [-1, 1]) {
      const ring = new THREE.TorusGeometry(ringR, s.width * 0.09, 6, 30);
      ring.rotateY(Math.PI / 2);
      ring.translate(sign * s.width * 0.34, 0, 0);
      parts.push(ring);
    }
    const hub = merge(parts);

    // rollers: two staggered rows, axes tangential to the rim
    const rParts = [];
    const step = (Math.PI * 2) / s.rollers;
    for (let row = 0; row < s.rows; row++) {
      const xOff = (row - (s.rows - 1) / 2) * s.width * 0.42;
      for (let i = 0; i < s.rollers; i++) {
        const a = i * step + (row % 2 ? step / 2 : 0);
        const g = barrelRoller(rollerLen * 2.0, rollerR);
        g.rotateZ(Math.PI / 2);                 // lathe axis Y -> X
        g.rotateX(a);                            // roll it round to sit tangentially
        g.rotateX(0);
        const m = new THREE.Matrix4().makeRotationX(a);
        const v = new THREE.Vector3(xOff, ringR, 0).applyMatrix4(m);
        g.translate(v.x, v.y, v.z);
        rParts.push(g);
      }
    }
    return { hub, rollers: merge(rParts) };
  });
}

/** VEX traction wheel: alloy hub + moulded tread. */
export function tractionWheel(kind = 'traction4') {
  return cached(`trac:${kind}`, () => {
    const s = C.WHEEL[kind];
    const hubParts = [];
    const web = new THREE.CylinderGeometry(s.od / 2 - 0.40, s.od / 2 - 0.40, s.width * 0.45, 26);
    web.rotateZ(Math.PI / 2); hubParts.push(web);
    const boss = new THREE.CylinderGeometry(0.42, 0.42, s.width, 18);
    boss.rotateZ(Math.PI / 2); hubParts.push(boss);

    const tireParts = [];
    const tire = new THREE.CylinderGeometry(s.od / 2 - 0.06, s.od / 2 - 0.06, s.width, 34);
    tire.rotateZ(Math.PI / 2); tireParts.push(tire);
    const ribs = 26;
    for (let i = 0; i < ribs; i++) {
      const a = (i / ribs) * Math.PI * 2;
      const rib = new THREE.BoxGeometry(s.width * 0.96, 0.085, 0.16);
      const m = new THREE.Matrix4().makeRotationX(a);
      rib.applyMatrix4(m);
      const v = new THREE.Vector3(0, s.od / 2 - 0.03, 0).applyMatrix4(m);
      rib.translate(v.x, v.y, v.z);
      tireParts.push(rib);
    }
    return { hub: merge(hubParts), tire: merge(tireParts) };
  });
}

/** Flex wheel / intake roller, axis along +X. */
export function flexWheel(od = 2.0, width = 0.5) {
  return cached(`flex:${od}:${width}`, () => {
    const parts = [];
    const body = new THREE.CylinderGeometry(od / 2, od / 2, width, 24);
    body.rotateZ(Math.PI / 2); parts.push(body);
    const hub = new THREE.CylinderGeometry(0.40, 0.40, width * 1.1, 16);
    hub.rotateZ(Math.PI / 2); parts.push(hub);
    return merge(parts);
  });
}

/* ================================================================= *
 * V5 ELECTRONICS
 * ================================================================= */

function roundedBox(l, w, h, r = 0.09) {
  const g = new THREE.ExtrudeGeometry(roundedRect(l, w, r), { depth: h, bevelEnabled: false, curveSegments: 6 });
  g.translate(0, 0, -h / 2);
  return g;
}

/**
 * V5 Smart Motor. Local frame: output shaft along +X at the origin,
 * body extending in -X. Bolt face is the +X face.
 */
export function v5Motor() {
  return cached('v5motor', () => {
    const m = C.V5.motor;
    const body = roundedBox(m.h, m.w, m.l, 0.12);   // built in XY then stood up
    body.rotateY(Math.PI / 2);                       // depth (l) -> X
    body.translate(-m.l / 2 - m.shaftBossH, 0, 0);
    const boss = new THREE.CylinderGeometry(m.shaftBossD / 2, m.shaftBossD / 2, m.shaftBossH, 20);
    boss.rotateZ(Math.PI / 2);
    boss.translate(-m.shaftBossH / 2, 0, 0);
    return merge([body, boss]);
  });
}

/** The coloured gear-cartridge ring on the motor face. */
export function v5MotorCartridge() {
  return cached('v5cart', () => {
    const g = new THREE.CylinderGeometry(C.V5.motor.shaftBossD / 2 + 0.02, C.V5.motor.shaftBossD / 2 + 0.02, 0.08, 20);
    g.rotateZ(Math.PI / 2);
    return g;
  });
}

/**
 * V5 Brain. Local frame: screen faces +Z, length along X, width along Y,
 * centred on the case.
 */
export function v5Brain() {
  return cached('v5brain', () => {
    const b = C.V5.brain;
    const shell = roundedBox(b.l, b.w, b.h, 0.10);
    const parts = [shell];
    // port strip down the long side
    for (let i = 0; i < 11; i++) {
      const p = new THREE.BoxGeometry(0.30, 0.12, 0.33);
      p.translate(-b.l / 2 + 0.55 + i * 0.33, b.w / 2, 0.05);
      parts.push(p);
    }
    return merge(parts);
  });
}

/** The brain's colour LCD, sitting just proud of the case's +Z face. */
export function v5BrainScreen() {
  return cached('v5screen', () => {
    const b = C.V5.brain;
    const g = new THREE.BoxGeometry(b.screenW, b.screenH, 0.02);
    g.translate(-0.25, 0, b.h / 2 + 0.01);
    return g;
  });
}

/** V5 Robot Battery. Length along X, width along Y, height along Z. */
export function v5Battery() {
  return cached('v5batt', () => roundedBox(C.V5.battery.l, C.V5.battery.w, C.V5.battery.h, 0.08));
}

/** V5 Radio. */
export function v5Radio() {
  return cached('v5radio', () => roundedBox(C.V5.radio.l, C.V5.radio.w, C.V5.radio.h, 0.06));
}
