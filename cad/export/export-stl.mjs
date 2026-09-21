/**
 * export-stl.mjs — write the assembly out as mesh files plus a bill of materials.
 *
 *   node export/export-stl.mjs
 *
 * Produces out/vex-robot.stl (binary, whole robot), out/vex-robot.obj,
 * one STL per subsystem, and the BOM as CSV and Markdown.
 */

import * as THREE from 'three';
import { STLExporter } from 'three/addons/exporters/STLExporter.js';
import { OBJExporter } from 'three/addons/exporters/OBJExporter.js';
import { buildRobot } from '../lib/robot.js';
import * as C from '../lib/vex-constants.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'out');
mkdirSync(join(OUT, 'subsystems'), { recursive: true });

const B = buildRobot();

/**
 * STLExporter does not expand InstancedMesh, so swap the instanced screws for
 * real meshes before exporting. (Cheap: one shared geometry, 200-odd matrices.)
 */
function expandInstances(root) {
  const swaps = [];
  root.traverse((o) => { if (o.isInstancedMesh) swaps.push(o); });
  for (const inst of swaps) {
    const g = new THREE.Group();
    g.name = inst.name;
    const m = new THREE.Matrix4();
    for (let i = 0; i < inst.count; i++) {
      inst.getMatrixAt(i, m);
      const mesh = new THREE.Mesh(inst.geometry, inst.material);
      mesh.applyMatrix4(m);
      mesh.name = `${inst.name}_${i}`;
      g.add(mesh);
    }
    inst.parent.add(g);
    inst.parent.remove(inst);
  }
  root.updateMatrixWorld(true);
  return swaps.reduce((a, s) => a + s.count, 0);
}
const expanded = expandInstances(B.root);

const stl = new STLExporter();
const obj = new OBJExporter();

const size = (n) => n > 1e6 ? (n / 1e6).toFixed(1) + ' MB' : (n / 1e3).toFixed(0) + ' kB';
const write = (name, data) => {
  const buf = data instanceof DataView ? Buffer.from(data.buffer) : Buffer.from(data, 'utf8');
  writeFileSync(join(OUT, name), buf);
  console.log(`  ${name.padEnd(34)} ${size(buf.length).padStart(9)}`);
};

console.log('\nwriting out/ ...');
write('vex-robot.stl', stl.parse(B.root, { binary: true }));
if (process.argv.includes('--obj')) write('vex-robot.obj', obj.parse(B.root));
for (const g of B.root.children) {
  write(`subsystems/${g.name}.stl`, stl.parse(g, { binary: true }));
}

/* --- bill of materials ------------------------------------------ */
const rows = [...B.bom.entries()].sort((a, b) => a[0].localeCompare(b[0]));
write('bom.csv', 'part,qty\n' + rows.map(([p, n]) => `"${p}",${n}`).join('\n') + '\n');

const md = [
  '# Bill of materials',
  '',
  ...B.notes.map((n) => `- **${n.k}:** ${n.v}`),
  '',
  '| Part | Qty |',
  '|---|---:|',
  ...rows.map(([p, n]) => `| ${p} | ${n} |`),
  '',
  `_${rows.reduce((a, [, n]) => a + n, 0)} modelled items across ${rows.length} line items._`,
  '',
].join('\n');
write('bom.md', md);

/* --- machine-readable summary ----------------------------------- */
let tris = 0;
B.root.traverse((o) => {
  if (!o.isMesh) return;
  const p = o.geometry.attributes.position;
  const n = (o.geometry.index ? o.geometry.index.count : p.count) / 3;
  tris += n * (o.isInstancedMesh ? o.count : 1);
});
write('summary.json', JSON.stringify({
  units: 'inch',
  envelope: {
    width: +B.envelope.width.toFixed(3),
    length: +B.envelope.length.toFixed(3),
    height: +B.envelope.height.toFixed(3),
    sizeLimit: C.SIZE_LIMIT,
    legal: B.envelope.legal,
  },
  notes: B.notes,
  bom: Object.fromEntries(rows),
  triangles: Math.round(tris),
}, null, 2) + '\n');

console.log(`\n${Math.round(tris).toLocaleString()} triangles, ${rows.length} BOM line items, ${expanded} fastener instances expanded.`);
console.log(`Envelope ${B.envelope.width.toFixed(2)} x ${B.envelope.length.toFixed(2)} x ${B.envelope.height.toFixed(2)} in.\n`);
