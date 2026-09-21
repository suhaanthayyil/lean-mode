/**
 * robot.js — the assembly.
 *
 * COORDINATE SYSTEM (inches)
 *   +X  robot's RIGHT
 *   +Y  robot's FRONT
 *   +Z  UP
 *   origin: centre of the drivebase footprint, at the floor (z = 0)
 *
 * Everything below is driven by the SPEC object. Measure the real robot,
 * change a number there, and the whole model follows — that is the point
 * of building this parametrically instead of pushing vertices around.
 */

import * as THREE from 'three';
import * as P from './vex-parts.js';
import * as C from './vex-constants.js';

/* ================================================================= *
 * SPEC — every design decision, in one editable block
 * ================================================================= */

export const SPEC = {
  drive: {
    // Odd hole counts put a hole ON the centreline, so the axle stations
    // at y = 0, +/-2.5, +/-5 all land on real holes.
    railLenHoles: 31,          // 1x5x1 outer drive rails -> 15.5" long
    innerRailLenHoles: 25,     // 1x5x1 inner rails -> 12.5", clear of the cross members
    // Both rails run flanges OUTBOARD: that leaves a flat inboard web face
    // for the motors to bolt to, and keeps the flanges out of the gear plane.
    outerRailX: 6.55,          // INBOARD face of the outer rail web
    innerRailX: 4.40,          // INBOARD face of the inner rail web
    wheelX: 5.95,              // wheel centre plane
    gearX: 5.15,               // gear-train plane, outboard of the inner rail flanges
    railZ: 3.00,               // centre of the rail web (holes at 2.0 .. 4.0)
    axleZ: 2.00,               // axle height == wheel radius
    motorZ: 4.00,              // motor shaft height (top hole row of the inner rail)
    stationY: [-5, -2.5, 0, 2.5, 5],   // gear-train stations, 2.5" = 60T mesh
    wheelStations: [0, 2, 4],  // which stations carry wheels
    motorStations: [1, 3],     // which stations are motor-driven
    gearTeeth: 60,             // idler/wheel gear
    pinionTeeth: 36,           // on the motor
    cartridge: 'blue',         // 600 rpm V5 cartridge
    frontWheel: 'omni4',
    centerWheel: 'traction4',
    rearWheel: 'omni4',
  },

  frame: {
    crossY: 7.25,              // front/rear cross members
    crossLenHoles: 26,         // 13.0"
    crossZ: 3.75,              // centre of the cross-member web
    deckZ: 4.25,               // top of the drive rails -> underside of the deck
    deckY: [-6.0, -1.0, 6.0],  // top-deck cross members (centre one carries the tower)
  },

  tower: {
    leanDeg: 24,               // lean aft from vertical
    baseY: -1.00,              // the tower foot, on the centre deck rail
    baseZ: 4.80,
    railLenHoles: 26,          // 13.0"
    railX: 3.60,               // OUTER face of each tower rail web
    chainX: 2.30,              // the two conveyor chain planes
    topShaftBack: 1.00,        // top shaft, down the rail axis from the top
    motorDown: 2.50,           // conveyor motor, down the axis from the top shaft
    gearX: 2.85,               // reduction gear plane (clears the rail flange)
    conveyorTeeth: 18,         // conveyor sprockets, top and bottom
    reductionGear: 84,         // on the top shaft
    reductionPinion: 36,       // on the motor
    cartridge: 'blue',
    flightEvery: 8,            // a carrier flight every N chain links
    crossAt: [0.25, 0.70, 0.90],   // cross standoffs, as a fraction of rail length
    braceX: 4.95,
    braceFootY: 6.50,
    braceTopFrac: 0.60,        // where the brace meets the tower, along its length
    armX: 3.05,                // the arms that carry the low intake shaft
    armFromFrac: 0.115,        // where the arms leave the tower
  },

  intake: {
    shaftY: 3.60,              // low intake / bottom conveyor shaft
    shaftZ: 2.40,
    flexX: 1.60,
    flexOd: 2.00,
  },

  electronics: {
    brain:   { x: -2.50, y: -4.00, z: 4.80 },
    battery: { x:  2.60, y: -4.60, z: 4.80 },
    radio:   { x:  0.00, y:  5.60, z: 4.80 },
  },
};

/* ================================================================= *
 * materials
 * ================================================================= */

const std = (color, o = {}) => new THREE.MeshStandardMaterial({
  color, metalness: 0.0, roughness: 0.55, ...o,
});

export const MAT = {
  aluminum: std(C.COLOR.aluminum, { metalness: 0.85, roughness: 0.34 }),
  steel:    std(C.COLOR.steel,    { metalness: 0.9,  roughness: 0.28 }),
  chain:    std(C.COLOR.chain,    { metalness: 0.9,  roughness: 0.32 }),
  red:      std(C.COLOR.vexRed,   { metalness: 0.05, roughness: 0.45 }),
  redLit:   std(C.COLOR.vexRedLit,{ metalness: 0.05, roughness: 0.40 }),
  black:    std(C.COLOR.black,    { metalness: 0.15, roughness: 0.60 }),
  dark:     std(C.COLOR.darkGray, { metalness: 0.25, roughness: 0.55 }),
  rubber:   std(C.COLOR.rubber,   { metalness: 0.0,  roughness: 0.92 }),
  roller:   std(C.COLOR.rollerGray,{ metalness: 0.0, roughness: 0.65 }),
  nylon:    std(0xf2f4f6,         { metalness: 0.0,  roughness: 0.70 }),
  screen:   new THREE.MeshStandardMaterial({
              color: C.COLOR.screen, emissive: 0x19527a, emissiveIntensity: 0.65,
              metalness: 0.1, roughness: 0.25 }),
};

/* ================================================================= *
 * placement helpers
 * ================================================================= */

const AX = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

/**
 * Compose a rotation from a list of world-frame steps applied in order.
 * orient(['x', a], ['z', b]) == "rotate about world X by a, then about world Z by b".
 */
export function orient(...steps) {
  const q = new THREE.Quaternion();
  for (const [axis, ang] of steps) {
    q.premultiply(new THREE.Quaternion().setFromAxisAngle(AX[axis], ang));
  }
  return q;
}

/** C-channel oriented web-vertical, length along +Y, web outer face pointing `side`*X. */
function qSideRail(side) {
  return orient(['x', -Math.PI / 2], ['z', side > 0 ? Math.PI / 2 : -Math.PI / 2]);
}
/** As above, then leaned by `alpha` about world X (for the tower and its braces). */
function qLeanRail(side, alpha) {
  return orient(['x', -Math.PI / 2], ['z', side > 0 ? Math.PI / 2 : -Math.PI / 2], ['x', alpha]);
}

const LOCAL = {
  /** centre of a C-channel's web OUTER face, in the part's own frame */
  webOuter: new THREE.Vector3(0, 0, -C.SHEET),
  origin: new THREE.Vector3(0, 0, 0),
};

/* ================================================================= *
 * builder
 * ================================================================= */

class Build {
  constructor() {
    this.root = new THREE.Group();
    this.root.name = 'robot';
    this.groups = {};
    this.bom = new Map();
    this.notes = [];
  }

  group(name) {
    if (!this.groups[name]) {
      const g = new THREE.Group();
      g.name = name;
      this.groups[name] = g;
      this.root.add(g);
    }
    return this.groups[name];
  }

  /** Record a line item for the bill of materials. */
  count(part, n = 1) {
    this.bom.set(part, (this.bom.get(part) || 0) + n);
  }

  /**
   * Place a cached geometry.
   * @param {string} groupName  subsystem this belongs to
   * @param {THREE.BufferGeometry} geom
   * @param {THREE.Material} mat
   * @param {object} o  { pos, q, anchor, explode, name, bom }
   */
  put(groupName, geom, mat, o = {}) {
    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const q = o.q || new THREE.Quaternion();
    mesh.quaternion.copy(q);
    const world = new THREE.Vector3().fromArray(o.pos || [0, 0, 0]);
    if (o.anchor) world.sub(o.anchor.clone().applyQuaternion(q));
    mesh.position.copy(world);
    mesh.name = o.name || 'part';
    mesh.userData.explode = o.explode || [0, 0, 0];
    mesh.userData.subsystem = groupName;
    if (o.spin) mesh.userData.spin = { ...o.spin, base: mesh.rotation.x };
    if (o.chainS !== undefined) {
      mesh.userData.chainS = o.chainS;
      mesh.userData.chainOut = o.chainOut;
    }
    this.group(groupName).add(mesh);
    if (o.bom) this.count(o.bom);
    return mesh;
  }
}

/* ================================================================= *
 * subassemblies
 * ================================================================= */

function buildDrivetrain(B) {
  const d = SPEC.drive;
  const G = 'drivetrain';
  const wheelRpm = () => C.CARTRIDGE[d.cartridge].rpm / (d.gearTeeth / d.pinionTeeth);

  for (const side of [-1, 1]) {
    // --- outer drive rail (1x5x1) and inner rail (1x5x1) -----------
    B.put(G, P.cChannel(d.railLenHoles, 5, 1), MAT.aluminum, {
      q: qSideRail(-side), anchor: LOCAL.webOuter,
      pos: [side * d.outerRailX, 0, d.railZ],
      explode: [side * 3, 0, 0],
      name: `drive rail ${side > 0 ? 'R' : 'L'}`,
      bom: `C-channel 1x5x1x${d.railLenHoles} (drive rail)`,
    });
    B.put(G, P.cChannel(d.innerRailLenHoles, 5, 1), MAT.aluminum, {
      q: qSideRail(-side),          // flanges outboard, flat face for the motors
      anchor: LOCAL.webOuter,
      pos: [side * d.innerRailX, 0, d.railZ],
      explode: [side * 1.4, 0, 0],
      name: `inner rail ${side > 0 ? 'R' : 'L'}`,
      bom: `C-channel 1x5x1x${d.innerRailLenHoles} (inner rail)`,
    });

    // --- axles, bearings, gears, wheels ----------------------------
    d.stationY.forEach((y, i) => {
      const isWheel = d.wheelStations.includes(i);
      const inner = d.innerRailX - 0.30, outer = d.outerRailX + 0.15;
      const shaftLen = outer - inner;
      const shaftX = side * (inner + shaftLen / 2);

      B.put(G, P.shaft(shaftLen, true), MAT.steel, {
        pos: [shaftX, y, d.axleZ], name: 'HS axle',
        explode: [side * 2, 0, 0],
        bom: `1/4" HS shaft (${shaftLen.toFixed(1)}")`,
      });

      // bearing flats where the axle passes through each rail
      for (const [bx, ex] of [[d.outerRailX, 2.6], [d.innerRailX, 1.2]]) {
        B.put(G, P.bearingFlat(), MAT.nylon, {
          q: orient(['y', Math.PI / 2]),
          pos: [side * bx, y, d.axleZ], name: 'bearing flat',
          explode: [side * ex, 0, 0],
          bom: 'Bearing flat',
        });
      }

      // the 60T gear train — every station carries one, so they all mesh
      B.put(G, P.gear(d.gearTeeth, true), MAT.red, {
        pos: [side * d.gearX, y, d.axleZ],
        q: new THREE.Quaternion().setFromAxisAngle(AX.x, (i % 2) * Math.PI / d.gearTeeth),
        name: `${d.gearTeeth}T drive gear`,
        explode: [side * 2.4, 0, 0],
        spin: { rpm: wheelRpm(), dir: i % 2 ? -1 : 1 },
        bom: `${d.gearTeeth}T HS gear`,
      });
      B.put(G, P.collar(true), MAT.steel, {
        pos: [side * (d.gearX + 0.32), y, d.axleZ], name: 'collar', bom: 'HS shaft collar',
        explode: [side * 2.4, 0, 0],
      });

      if (isWheel) {
        const kind = i === d.wheelStations[0] ? d.rearWheel
                   : i === d.wheelStations[2] ? d.frontWheel : d.centerWheel;
        if (kind.startsWith('omni')) {
          const w = P.omniWheel(kind);
          const sp = { rpm: wheelRpm(), dir: 1 };
          B.put(G, w.hub, MAT.dark, { pos: [side * d.wheelX, y, d.axleZ], name: '4" omni hub',
            explode: [side * 3.4, 0, 0], bom: '4" Omni wheel', spin: sp });
          B.put(G, w.rollers, MAT.roller, { pos: [side * d.wheelX, y, d.axleZ], name: '4" omni rollers',
            explode: [side * 3.4, 0, 0], spin: sp });
        } else {
          const w = P.tractionWheel(kind);
          const sp = { rpm: wheelRpm(), dir: 1 };
          B.put(G, w.hub, MAT.dark, { pos: [side * d.wheelX, y, d.axleZ], name: '4" traction hub',
            explode: [side * 3.4, 0, 0], bom: '4" Traction wheel', spin: sp });
          B.put(G, w.tire, MAT.rubber, { pos: [side * d.wheelX, y, d.axleZ], name: '4" traction tyre',
            explode: [side * 3.4, 0, 0], spin: sp });
        }
      }
    });

    // --- drive motors ---------------------------------------------
    for (const st of d.motorStations) {
      const y = d.stationY[st];
      B.put('electronics', P.v5Motor(), MAT.black, {
        q: orient(['y', side > 0 ? 0 : Math.PI]),
        pos: [side * d.innerRailX, y, d.motorZ],
        name: 'V5 Smart Motor (drive)', explode: [side * 1.0, 0, 1.5],
        bom: 'V5 Smart Motor 11W',
      });
      B.put('electronics', P.v5MotorCartridge(), MAT.red, {
        pos: [side * (d.innerRailX + 0.18), y, d.motorZ],
        name: `${C.CARTRIDGE[d.cartridge].rpm} rpm cartridge`,
        explode: [side * 1.0, 0, 1.5],
      });
      // pinion, meshing the station gear 2.0" below it
      B.put(G, P.gear(d.pinionTeeth, true), MAT.red, {
        pos: [side * d.gearX, y, d.motorZ], name: `${d.pinionTeeth}T pinion`,
        explode: [side * 2.4, 0, 1.5], bom: `${d.pinionTeeth}T HS gear`,
        spin: { rpm: C.CARTRIDGE[d.cartridge].rpm, dir: st % 2 ? 1 : -1 },
      });
      B.put(G, P.shaft(1.6, true), MAT.steel, {
        pos: [side * (d.innerRailX + 0.55), y, d.motorZ], name: 'motor shaft',
        explode: [side * 2.0, 0, 1.5], bom: '1/4" HS shaft (1.6")',
      });
    }
  }

  const ratio = d.gearTeeth / d.pinionTeeth;
  const rpm = wheelRpm();
  const od = C.WHEEL[d.frontWheel].od;
  B.notes.push({
    k: 'Drive gearing',
    v: `${d.pinionTeeth}T → ${d.gearTeeth}T (${ratio.toFixed(2)}:1) on a ${C.CARTRIDGE[d.cartridge].rpm} rpm cartridge`,
  });
  B.notes.push({
    k: 'Free speed',
    v: `${rpm.toFixed(0)} rpm × ${od}" wheel = ${(rpm * Math.PI * od / 60).toFixed(1)} in/s (${(rpm * Math.PI * od / 720).toFixed(2)} ft/s)`,
  });
}

function buildFrame(B) {
  const f = SPEC.frame, d = SPEC.drive;
  const G = 'frame';

  // front / rear cross members, web vertical facing outward
  for (const s of [1, -1]) {
    B.put(G, P.cChannel(f.crossLenHoles, 2, 1), MAT.aluminum, {
      q: orient(['x', s > 0 ? Math.PI / 2 : -Math.PI / 2]),
      anchor: LOCAL.webOuter,
      pos: [0, s * f.crossY, f.crossZ],
      explode: [0, s * 3, 0],
      name: s > 0 ? 'front cross member' : 'rear cross member',
      bom: `C-channel 1x2x1x${f.crossLenHoles} (cross member)`,
    });
  }

  // top deck: web horizontal, flanges up, sitting on the drive rails
  for (const y of f.deckY) {
    B.put(G, P.cChannel(f.crossLenHoles, 2, 1), MAT.aluminum, {
      anchor: LOCAL.webOuter,
      pos: [0, y, f.deckZ],
      explode: [0, 0, 3],
      name: `deck rail y=${y}`,
      bom: `C-channel 1x2x1x${f.crossLenHoles} (deck rail)`,
    });
  }

  // corner gussets tying the deck rails to the drive rails
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    B.put(G, P.angleBar(5, 1, 1), MAT.aluminum, {
      q: orient(['z', sx * sy > 0 ? 0 : Math.PI]),
      pos: [sx * (d.outerRailX - 1.3), sy * (f.crossY - 0.30), f.deckZ - 0.05],
      explode: [sx * 2, sy * 2, 1],
      name: 'corner gusset', bom: 'Angle 1x1x5',
    });
  }
}


/* ================================================================= *
 * tower + conveyor
 * ================================================================= */

/** Resolve the tower's axis geometry once; several builders need it. */
export function towerGeometry() {
  const t = SPEC.tower;
  const lean = THREE.MathUtils.degToRad(t.leanDeg);
  const u = new THREE.Vector2(-Math.sin(lean), Math.cos(lean));   // (y, z), up and aft
  const L = C.holes(t.railLenHoles);
  const base = new THREE.Vector2(t.baseY, t.baseZ);
  const top = base.clone().add(u.clone().multiplyScalar(L));
  const mid = base.clone().add(u.clone().multiplyScalar(L / 2));
  const topShaft = top.clone().sub(u.clone().multiplyScalar(t.topShaftBack));
  const motorShaft = topShaft.clone().sub(u.clone().multiplyScalar(t.motorDown));
  const botShaft = new THREE.Vector2(SPEC.intake.shaftY, SPEC.intake.shaftZ);
  return { lean, u, L, base, top, mid, topShaft, motorShaft, botShaft,
           alpha: Math.PI / 2 + lean,
           at: (f) => base.clone().add(u.clone().multiplyScalar(L * f)) };
}

/** Angle about world X that takes a part's +Y length axis onto (dy, dz). */
const alphaFor = (dy, dz) => Math.atan2(dz, dy);

function buildTower(B) {
  const t = SPEC.tower, T = towerGeometry();
  const G = 'tower';

  // --- the two tower rails --------------------------------------
  for (const side of [-1, 1]) {
    B.put(G, P.cChannel(t.railLenHoles, 2, 1), MAT.aluminum, {
      q: qLeanRail(side, T.alpha), anchor: LOCAL.webOuter,
      pos: [side * t.railX, T.mid.x, T.mid.y],
      explode: [side * 2.5, 0, 2],
      name: `tower rail ${side > 0 ? 'R' : 'L'}`,
      bom: `C-channel 1x2x1x${t.railLenHoles} (tower rail)`,
    });
  }

  // --- cross standoffs tying the two rails together --------------
  const soLen = 2 * t.railX - 2 * C.SHEET;
  for (const f of t.crossAt) {
    const p = T.at(f);
    B.put(G, P.standoff(soLen), MAT.aluminum, {
      q: orient(['y', Math.PI / 2]),
      pos: [0, p.x, p.y], explode: [0, 0, 2.5],
      name: 'tower cross standoff', bom: `Standoff ${soLen.toFixed(1)}"`,
    });
  }

  // --- A-frame braces, front of the chassis up to the tower ------
  {
    const topPt = T.at(t.braceTopFrac);
    const foot = new THREE.Vector2(t.braceFootY, SPEC.frame.deckZ + 0.55);
    const d = topPt.clone().sub(foot);
    const nHoles = Math.round(d.length() / C.PITCH);
    const mid = foot.clone().add(d.clone().multiplyScalar(0.5));
    for (const side of [-1, 1]) {
      B.put(G, P.cChannel(nHoles, 2, 1), MAT.aluminum, {
        q: qLeanRail(side, alphaFor(d.x, d.y)), anchor: LOCAL.webOuter,
        pos: [side * t.braceX, mid.x, mid.y],
        explode: [side * 2.5, 2, 1],
        name: `A-frame brace ${side > 0 ? 'R' : 'L'}`,
        bom: `C-channel 1x2x1x${nHoles} (A-frame brace)`,
      });
      // standoff closing the gap between the brace and the tower rail
      const gap = t.braceX - t.railX;
      B.put(G, P.standoff(gap), MAT.aluminum, {
        q: orient(['y', Math.PI / 2]),
        pos: [side * (t.railX + gap / 2), topPt.x, topPt.y],
        explode: [side * 2.5, 2, 1],
        name: 'brace standoff', bom: `Standoff ${gap.toFixed(2)}"`,
      });
    }
    B.notes.push({ k: 'A-frame brace', v: `1x2x1x${nHoles} each side, ${(d.length()).toFixed(1)}" between centres` });
  }

  // --- arms carrying the low intake / bottom conveyor shaft ------
  {
    const from = T.at(t.armFromFrac);
    const d = T.botShaft.clone().sub(from);
    const nHoles = Math.round(d.length() / C.PITCH);
    const mid = from.clone().add(d.clone().multiplyScalar(0.5));
    for (const side of [-1, 1]) {
      B.put(G, P.cChannel(nHoles, 2, 1), MAT.aluminum, {
        q: qLeanRail(side, alphaFor(d.x, d.y)), anchor: LOCAL.webOuter,
        pos: [side * t.armX, mid.x, mid.y],
        explode: [side * 2.0, 2, -1],
        name: `intake arm ${side > 0 ? 'R' : 'L'}`,
        bom: `C-channel 1x2x1x${nHoles} (intake arm)`,
      });
    }
  }

  // --- shafts ----------------------------------------------------
  const shaftLen = 2 * t.railX + 0.6;
  for (const [pt, nm] of [[T.topShaft, 'top conveyor shaft'], [T.botShaft, 'lower conveyor shaft']]) {
    B.put(G, P.shaft(shaftLen, true), MAT.steel, {
      pos: [0, pt.x, pt.y], name: nm, explode: [0, 0, 3],
      bom: `1/4" HS shaft (${shaftLen.toFixed(1)}")`,
    });
    for (const side of [-1, 1]) {
      B.put(G, P.bearingFlat(), MAT.nylon, {
        q: orient(['y', Math.PI / 2]),
        pos: [side * t.railX, pt.x, pt.y], name: 'bearing flat',
        explode: [side * 2.5, 0, 3], bom: 'Bearing flat',
      });
    }
  }

  // --- the two conveyor chain loops ------------------------------
  const convRpm = C.CARTRIDGE[t.cartridge].rpm / (t.reductionGear / t.reductionPinion);
  const loop = P.chainLoop(
    { y: T.botShaft.x, z: T.botShaft.y, teeth: t.conveyorTeeth },
    { y: T.topShaft.x, z: T.topShaft.y, teeth: t.conveyorTeeth });

  for (const side of [-1, 1]) {
    B.put(G, loop.geometry, MAT.chain, {
      pos: [side * t.chainX, 0, 0],
      name: `conveyor chain ${side > 0 ? 'R' : 'L'}`,
      explode: [side * 1.2, 0, 3],
      bom: `#25 chain, ${loop.links} links`,
    });
    // sprockets, phased so their seats sit under the rollers
    B.put(G, P.sprocket(t.conveyorTeeth, true), MAT.red, {
      q: new THREE.Quaternion().setFromAxisAngle(AX.x, loop.phaseA),
      pos: [side * t.chainX, T.botShaft.x, T.botShaft.y],
      name: `${t.conveyorTeeth}T sprocket (lower)`, explode: [side * 1.6, 0, 3],
      spin: { rpm: convRpm, dir: 1 },
      bom: `${t.conveyorTeeth}T HS sprocket`,
    });
    B.put(G, P.sprocket(t.conveyorTeeth, true), MAT.red, {
      q: new THREE.Quaternion().setFromAxisAngle(AX.x, loop.phaseB),
      pos: [side * t.chainX, T.topShaft.x, T.topShaft.y],
      name: `${t.conveyorTeeth}T sprocket (upper)`, explode: [side * 1.6, 0, 3],
      spin: { rpm: convRpm, dir: 1 },
      bom: `${t.conveyorTeeth}T HS sprocket`,
    });
  }

  // --- carrier flights, bridging the two chains ------------------
  {
    const centre = new THREE.Vector2(
      (T.botShaft.x + T.topShaft.x) / 2, (T.botShaft.y + T.topShaft.y) / 2);
    const span = 2 * t.chainX - 0.25;
    const flightG = new THREE.BoxGeometry(span, 0.20, 0.62);
    let n = 0;
    for (let i = 0; i < loop.links; i += t.flightEvery) {
      const p = loop.at(i * loop.pitchUsed);
      // push the flight outward, away from the middle of the loop
      let nx = -Math.sin(p.dir), ny = Math.cos(p.dir);
      if ((p.y - centre.x) * nx + (p.z - centre.y) * ny < 0) { nx = -nx; ny = -ny; }
      const out = 0.46;
      B.put(G, flightG, MAT.redLit, {
        q: orient(['x', Math.atan2(ny, nx) - Math.PI / 2]),
        pos: [0, p.y + nx * out, p.z + ny * out],
        name: 'carrier flight', explode: [0, 0, 3.5],
        chainS: i * loop.pitchUsed, chainOut: out,
      });
      n++;
    }
    B.count(`Carrier flight (3D printed)`);
    B.bom.set('Carrier flight (3D printed)', n);
  }

  // --- reduction: motor 36T -> 84T on the top shaft --------------
  B.put(G, P.gear(t.reductionGear, true), MAT.red, {
    pos: [-t.gearX, T.topShaft.x, T.topShaft.y],
    name: `${t.reductionGear}T HS gear`, explode: [-2.0, 0, 3],
    spin: { rpm: convRpm, dir: 1 },
    bom: `${t.reductionGear}T HS gear`,
  });
  B.put(G, P.gear(t.reductionPinion, true), MAT.red, {
    pos: [-t.gearX, T.motorShaft.x, T.motorShaft.y],
    name: `${t.reductionPinion}T HS pinion`, explode: [-2.0, 0, 2],
    spin: { rpm: C.CARTRIDGE[t.cartridge].rpm, dir: -1 },
    bom: `${t.reductionPinion}T HS gear`,
  });
  B.put(G, P.shaft(1.8, true), MAT.steel, {
    pos: [-t.railX - 0.2, T.motorShaft.x, T.motorShaft.y],
    name: 'conveyor motor shaft', explode: [-2.0, 0, 2], bom: '1/4" HS shaft (1.8")',
  });
  B.put('electronics', P.v5Motor(), MAT.black, {
    q: orient(['x', -T.lean]),
    pos: [-t.railX, T.motorShaft.x, T.motorShaft.y],
    name: 'V5 Smart Motor (conveyor)', explode: [-3.0, 0, 2],
    bom: 'V5 Smart Motor 11W',
  });
  B.put('electronics', P.v5MotorCartridge(), MAT.red, {
    pos: [-t.railX - 0.18, T.motorShaft.x, T.motorShaft.y],
    name: `${C.CARTRIDGE[t.cartridge].rpm} rpm cartridge`, explode: [-3.0, 0, 2],
  });

  const ratio = t.reductionGear / t.reductionPinion;
  const rpm = C.CARTRIDGE[t.cartridge].rpm / ratio;
  const chainSpeed = rpm * Math.PI * C.sprocketPD(t.conveyorTeeth) / 60;
  B.notes.push({ k: 'Conveyor gearing', v: `${t.reductionPinion}T → ${t.reductionGear}T (${ratio.toFixed(2)}:1) on a ${C.CARTRIDGE[t.cartridge].rpm} rpm cartridge` });
  B.notes.push({ k: 'Chain speed', v: `${rpm.toFixed(0)} rpm × ${C.sprocketPD(t.conveyorTeeth).toFixed(2)}" PD = ${chainSpeed.toFixed(1)} in/s` });
  B.notes.push({ k: 'Chain loop', v: `${loop.links} links of #25 (${loop.lengthIn.toFixed(1)}" per loop), ${(2 * loop.links)} links total` });
  B.notes.push({ k: 'Tower lean', v: `${t.leanDeg}° aft of vertical` });
  B.chainLoop = loop;
  B.chainCentre = [(T.botShaft.x + T.topShaft.x) / 2, (T.botShaft.y + T.topShaft.y) / 2];
  B.chainSpeed = convRpm * Math.PI * C.sprocketPD(t.conveyorTeeth) / 60;  // in/s
  return loop;
}

/* ================================================================= *
 * intake (flex wheels on the lower conveyor shaft)
 * ================================================================= */

function buildIntake(B) {
  const i = SPEC.intake;
  for (const side of [-1, 1]) {
    B.put('intake', P.flexWheel(i.flexOd, 0.55), MAT.dark, {
      pos: [side * i.flexX, i.shaftY, i.shaftZ],
      name: `${i.flexOd}" flex wheel`, explode: [side * 1.5, 1.5, -1],
      bom: `${i.flexOd}" Flex wheel`,
    });
    B.put('intake', P.collar(true), MAT.steel, {
      pos: [side * (i.flexX + 0.45), i.shaftY, i.shaftZ],
      name: 'collar', explode: [side * 1.5, 1.5, -1], bom: 'HS shaft collar',
    });
  }
  B.notes.push({ k: 'Intake', v: `2 × ${i.flexOd}" flex wheels on the lower conveyor shaft, ${i.shaftZ - i.flexOd / 2}" ground clearance` });
}

/* ================================================================= *
 * electronics
 * ================================================================= */

function buildElectronics(B) {
  const e = SPEC.electronics, G = 'electronics';

  B.put(G, P.v5Brain(), MAT.dark, {
    pos: [e.brain.x, e.brain.y, e.brain.z + C.V5.brain.h / 2],
    name: 'V5 Robot Brain', explode: [0, -2, 4], bom: 'V5 Robot Brain',
  });
  B.put(G, P.v5BrainScreen(), MAT.screen, {
    pos: [e.brain.x, e.brain.y, e.brain.z + C.V5.brain.h / 2],
    name: 'V5 brain screen', explode: [0, -2, 4],
  });
  B.put(G, P.v5Battery(), MAT.black, {
    pos: [e.battery.x, e.battery.y, e.battery.z + C.V5.battery.h / 2],
    name: 'V5 Robot Battery', explode: [0, -2, 4], bom: 'V5 Robot Battery',
  });
  B.put(G, P.v5Radio(), MAT.black, {
    pos: [e.radio.x, e.radio.y, e.radio.z + C.V5.radio.h / 2],
    name: 'V5 Radio', explode: [0, 2, 4], bom: 'V5 Radio',
  });
}

/* ================================================================= *
 * fasteners  (one InstancedMesh, so a few hundred screws stay cheap)
 * ================================================================= */

function buildFasteners(B) {
  const d = SPEC.drive, f = SPEC.frame, t = SPEC.tower, T = towerGeometry();
  const sites = [];   // { pos:[x,y,z], normal:[x,y,z] }

  // bearing flats: two screws on the diagonal, driven inward through the rail
  const bearingSites = (x, y, z, nx) => {
    for (const [dy, dz] of [[-C.PITCH / 2, C.PITCH / 2], [C.PITCH / 2, -C.PITCH / 2]]) {
      sites.push({ pos: [x, y + dy, z + dz], normal: [nx, 0, 0] });
    }
  };
  for (const side of [-1, 1]) {
    for (const y of d.stationY) {
      bearingSites(side * (d.outerRailX + 0.001), y, d.axleZ, side);
      bearingSites(side * (d.innerRailX + 0.001) * 1, y, d.axleZ, side);
    }
    // deck rails onto the drive rails
    for (const y of f.deckY) {
      for (const dx of [-0.25, 0.25]) {
        sites.push({ pos: [side * (d.outerRailX - 1.0) + dx, y, f.deckZ + 0.50], normal: [0, 0, 1] });
      }
    }
    // tower rail feet + bearings
    for (const pt of [T.topShaft, T.botShaft]) bearingSites(side * (t.railX + 0.001), pt.x, pt.y, side);
    // motor bolt circles
    for (const yy of d.motorStations.map((i) => d.stationY[i])) {
      for (const [a, b] of [[-0.5, 0.5], [0.5, 0.5], [-0.5, -0.5], [0.5, -0.5]]) {
        sites.push({ pos: [side * (d.innerRailX + 0.001), yy + a, d.motorZ + b], normal: [side, 0, 0] });
      }
    }
  }
  // front/rear cross members
  for (const sy of [-1, 1]) for (const x of [-5.25, -2.25, 2.25, 5.25]) {
    sites.push({ pos: [x, sy * (f.crossY + 0.001), f.crossZ + 0.25], normal: [0, sy, 0] });
  }

  const geom = P.screw(0.5);
  const mesh = new THREE.InstancedMesh(geom, MAT.steel, sites.length);
  mesh.name = 'screws';
  mesh.userData.subsystem = 'fasteners';
  mesh.userData.explode = [0, 0, 0];
  const m = new THREE.Matrix4(), q = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 0, 1), n = new THREE.Vector3(), s = new THREE.Vector3(1, 1, 1);
  sites.forEach((site, idx) => {
    n.fromArray(site.normal).normalize();
    q.setFromUnitVectors(up, n);
    m.compose(new THREE.Vector3().fromArray(site.pos), q, s);
    mesh.setMatrixAt(idx, m);
  });
  mesh.instanceMatrix.needsUpdate = true;
  mesh.castShadow = true;
  B.group('fasteners').add(mesh);
  B.bom.set('8-32 screw + nylock (modelled)', sites.length);
  return sites.length;
}

/* ================================================================= *
 * top-level build
 * ================================================================= */

export function buildRobot() {
  const B = new Build();
  buildDrivetrain(B);
  buildFrame(B);
  buildTower(B);
  buildIntake(B);
  buildElectronics(B);
  buildFasteners(B);

  const box = new THREE.Box3().setFromObject(B.root);
  const size = box.getSize(new THREE.Vector3());
  B.envelope = {
    width: size.x, length: size.y, height: size.z,
    box,
    legal: Math.max(size.x, size.y, size.z) <= C.SIZE_LIMIT,
  };
  B.notes.unshift({
    k: 'Envelope',
    v: `${size.x.toFixed(2)}" W × ${size.y.toFixed(2)}" L × ${size.z.toFixed(2)}" H` +
       ` — ${B.envelope.legal ? 'inside' : 'OUTSIDE'} the ${C.SIZE_LIMIT}" starting cube`,
  });
  return B;
}

export { buildDrivetrain, buildFrame, buildTower, buildIntake, buildElectronics,
         buildFasteners, Build, AX, qSideRail, qLeanRail, LOCAL };
