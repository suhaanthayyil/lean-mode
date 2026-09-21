/**
 * check.mjs — engineering checks on the assembly.
 *
 * 1. every gear pair sharing a plane is either exactly meshing at the DP24
 *    centre distance, or clear of the other's tip circle
 * 2. sprockets sharing a plane never touch
 * 3. the chain loops close on a whole number of links at ~0.25" pitch
 * 4. solid-body interference, by testing each part's vertices against the
 *    other part's oriented box (broad-phased on world AABBs first)
 * 5. the robot fits the 18" starting cube and clears the floor
 */

import * as THREE from 'three';
import { buildRobot, towerGeometry, SPEC } from '../lib/robot.js';
import * as C from '../lib/vex-constants.js';
import * as P from '../lib/vex-parts.js';

const B = buildRobot();
let fails = 0, warns = 0;
const ok   = (m) => console.log('  \x1b[32mPASS\x1b[0m ' + m);
const bad  = (m) => { fails++; console.log('  \x1b[31mFAIL\x1b[0m ' + m); };
const warn = (m) => { warns++; console.log('  \x1b[33mWARN\x1b[0m ' + m); };

/* --- collect the toothed parts ---------------------------------- */
const toothed = [];
B.root.traverse((o) => {
  if (!o.isMesh || o.isInstancedMesh) return;
  const m = /^(\d+)T/.exec(o.name);
  if (!m) return;
  const p = new THREE.Vector3();
  o.getWorldPosition(p);
  toothed.push({
    name: o.name, teeth: +m[1], p,
    kind: /sprocket/i.test(o.name) ? 'sprocket' : 'gear',
    od: /sprocket/i.test(o.name) ? C.sprocketPD(+m[1]) + 0.17 : C.gearOD(+m[1]),
  });
});

console.log(`\n=== 1. gear meshing (${toothed.filter((t) => t.kind === 'gear').length} gears) ===`);
let meshes = 0, clears = 0;
for (let i = 0; i < toothed.length; i++) {
  for (let j = i + 1; j < toothed.length; j++) {
    const a = toothed[i], b = toothed[j];
    if (Math.abs(a.p.x - b.p.x) > 0.02) continue;            // different planes
    const d = Math.hypot(a.p.y - b.p.y, a.p.z - b.p.z);
    if (d < 1e-6) continue;                                   // coaxial
    const tipSum = (a.od + b.od) / 2;
    if (a.kind === 'gear' && b.kind === 'gear') {
      const want = C.meshDistance(a.teeth, b.teeth);
      if (Math.abs(d - want) < 0.015) { meshes++; continue; }
      if (d < tipSum - 0.01) {
        bad(`${a.teeth}T @${a.p.y.toFixed(2)},${a.p.z.toFixed(2)} vs ${b.teeth}T @${b.p.y.toFixed(2)},${b.p.z.toFixed(2)}: centres ${d.toFixed(3)}" but tips need ${tipSum.toFixed(3)}"`);
      } else clears++;
    } else if (d < tipSum - 0.01) {
      bad(`${a.name} and ${b.name} overlap: ${d.toFixed(3)}" apart, need ${tipSum.toFixed(3)}"`);
    } else clears++;
  }
}
ok(`${meshes} meshing pairs at the exact DP24 centre distance`);
ok(`${clears} coplanar non-meshing pairs clear of each other's tip circles`);

/* --- 2. chain --------------------------------------------------- */
console.log('\n=== 2. #25 chain ===');
{
  const T = towerGeometry();
  const loop = P.chainLoop(
    { y: T.botShaft.x, z: T.botShaft.y, teeth: SPEC.tower.conveyorTeeth },
    { y: T.topShaft.x, z: T.topShaft.y, teeth: SPEC.tower.conveyorTeeth });
  const err = Math.abs(loop.pitchUsed - C.CHAIN_PITCH) / C.CHAIN_PITCH;
  (err < 0.01 ? ok : bad)(`loop closes on ${loop.links} links at ${loop.pitchUsed.toFixed(4)}" pitch (${(err * 100).toFixed(2)}% off nominal 0.25")`);
  (loop.links % 2 === 0 ? ok : warn)(`${loop.links} links — #25 chain wants an even link count to close with one master link`);
}

/* --- 3. solid interference -------------------------------------- */
console.log('\n=== 3. solid interference ===');
const solids = [];
B.root.updateMatrixWorld(true);
B.root.traverse((o) => {
  if (!o.isMesh || o.isInstancedMesh) return;
  const g = o.geometry;
  if (!g.boundingBox) g.computeBoundingBox();
  const world = new THREE.Box3().copy(g.boundingBox).applyMatrix4(o.matrixWorld);
  solids.push({ o, local: g.boundingBox, world, inv: new THREE.Matrix4().copy(o.matrixWorld).invert() });
});

// parts that touch by design: fasteners, bearings, collars, anything on a shaft
// The box test cannot see through the holes that are cut in the material, so
// anything designed to pass THROUGH a part (axles, screws, bearings) is
// declared here rather than being reported as a clash.
const CONTACT_OK = /screw|bearing|collar|shaft|axle|gusset|standoff|cartridge|chain|flight|roller|tyre|hub|screen/i;
/**
 * Mating faces — pairs that are bolted to each other and are SUPPOSED to be
 * in contact. Declared explicitly rather than loosening the tolerance, so a
 * genuine clash elsewhere still fails the check.
 */
const JOINTS = [
  [/deck rail/, /brace|tower rail|intake arm/],
  [/drive rail|inner rail/, /cross member|deck rail/],
  [/tower rail/, /brace|intake arm/],
  [/cross member/, /deck rail/],
];
const isJoint = (a, b) => JOINTS.some(([x, y]) =>
  (x.test(a) && y.test(b)) || (x.test(b) && y.test(a)));
const EPS = 0.02;
let pairs = 0, hits = [];
for (let i = 0; i < solids.length; i++) {
  for (let j = i + 1; j < solids.length; j++) {
    const A = solids[i], Bb = solids[j];
    if (!A.world.intersectsBox(Bb.world)) continue;
    if (CONTACT_OK.test(A.o.name) || CONTACT_OK.test(Bb.o.name)) continue;
    if (isJoint(A.o.name, Bb.o.name)) continue;
    pairs++;
    // sample A's vertices in B's local frame
    const pos = A.o.geometry.attributes.position;
    const v = new THREE.Vector3();
    const shrunk = Bb.local.clone().expandByScalar(-EPS);
    let inside = 0, deepest = 0;
    const stride = Math.max(1, Math.floor(pos.count / 900));
    for (let k = 0; k < pos.count; k += stride) {
      v.fromBufferAttribute(pos, k).applyMatrix4(A.o.matrixWorld).applyMatrix4(Bb.inv);
      if (shrunk.containsPoint(v)) {
        inside++;
        const d = Math.min(
          v.x - shrunk.min.x, shrunk.max.x - v.x,
          v.y - shrunk.min.y, shrunk.max.y - v.y,
          v.z - shrunk.min.z, shrunk.max.z - v.z);
        deepest = Math.max(deepest, d);
      }
    }
    if (inside > 2 && deepest > 0.03) hits.push({ a: A.o.name, b: Bb.o.name, inside, deepest });
  }
}
hits.sort((x, y) => y.deepest - x.deepest);
if (!hits.length) ok(`no interference across ${pairs} candidate pairs`);
for (const h of hits.slice(0, 12)) {
  bad(`"${h.a}" ∩ "${h.b}" — ${h.inside} sampled points inside, up to ${h.deepest.toFixed(3)}" deep`);
}
if (hits.length > 12) console.log(`  ... and ${hits.length - 12} more`);

/* --- 4. envelope ------------------------------------------------ */
console.log('\n=== 4. competition envelope ===');
const e = B.envelope;
(e.legal ? ok : bad)(`${e.width.toFixed(2)}" W × ${e.length.toFixed(2)}" L × ${e.height.toFixed(2)}" H vs the ${C.SIZE_LIMIT}" starting cube`);
const floor = e.box.min.z;
(Math.abs(floor) < 0.05 ? ok : warn)(`lowest point at z = ${floor.toFixed(3)}" (wheels should touch z = 0)`);

console.log(`\n${fails ? '\x1b[31m' : '\x1b[32m'}${fails} failed, ${warns} warnings\x1b[0m\n`);
process.exit(fails ? 1 : 0);
