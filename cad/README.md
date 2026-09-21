# VEX V5 robot — parametric CAD

A full CAD model of the team's VEX V5RC robot, built as **parametric code** rather than
pushed around in a GUI. Every part is generated from the real VEX dimensional standard
(0.5" hole pitch, DP24 gears, #25 chain, V5 electronics envelopes), so changing one number
in the spec block rebuilds the whole assembly consistently.

```
cad/
  index.html            interactive 3D viewer (open it in a browser)
  lib/
    vex-constants.js    the VEX dimensional standard — pitch, DP24, #25, V5 envelopes
    vex-parts.js        part factories: C-channel, angle, gears, sprockets, chain, wheels, V5
    robot.js            the assembly: SPEC block + subassembly builders + BOM
  export/
    check.mjs           engineering checks (gear mesh, chain, interference, size limit)
    export-stl.mjs      writes STL / OBJ / BOM / summary.json into out/
```

## Use it

```bash
cd cad
npm install          # three.js only
npm run check        # verify the model
npm run export       # write out/vex-robot.stl, per-subsystem STLs, bom.md, bom.csv
npx serve . && open http://localhost:3000/   # or any static server, for the viewer
```

The viewer needs a static server (it loads ES modules); opening `index.html` from `file://`
will not work.

## What is modelled

**Drivetrain** — 6-wheel gear-linked tank drive, 4" omni at each corner and a 4" traction
wheel in the centre of each side. Five gear stations per side at 2.5" spacing (the exact
60T–60T DP24 centre distance) so the whole side turns as one train. Two V5 motors per side
drive through a 36T pinion onto the train, 2.000" above the axle line — again the exact
36T/60T centre distance. On 600 rpm (blue) cartridges that is **360 rpm at the wheel,
6.28 ft/s**.

**Tower and conveyor** — two 1x2x1 rails leaning 24° aft, braced forward by an A-frame to
the front of the chassis and tied together by three cross standoffs. Two #25 chain loops
(150 links each) run from a low intake shaft at the front up to the top shaft, carrying
19 flights. A single V5 motor drives it through 36T → 84T (2.33:1), giving **19.4 in/s of
chain speed**.

**Intake** — two 2" flex wheels share the lower conveyor shaft, so the same chain that
carries game elements up the tower also pulls them in at floor level. 1.4" ground clearance.

**Electronics** — V5 Brain, battery, radio and five V5 Smart Motors, placed as real
volumes so they are checked for interference like everything else.

**Envelope** — 14.20" W × 15.50" L × 17.56" H. Inside the 18" starting cube, with the
tightest dimension at 98% of the limit.

## The checks

`npm run check` is not a smoke test — it is the reason to trust the model:

1. **Gear meshing.** Every pair of toothed parts sharing a plane must either sit at the
   exact DP24 centre distance `(t1+t2)/48`, or be clear of the other's tip circle. 13 pairs
   mesh exactly; 32 coplanar pairs are verified clear.
2. **Chain.** The loop must close on a whole, even number of links within 1% of the 0.25"
   nominal pitch.
3. **Interference.** Each part's vertices are transformed into every overlapping part's own
   frame and tested against its box. Parts designed to pass *through* material (axles,
   screws, bearings) and declared mating faces (bolted joints) are listed explicitly rather
   than the tolerance being loosened, so a real clash still fails.
4. **Envelope.** The assembly must fit the 18" cube and the wheels must touch z = 0.

## Coordinates and units

Inches throughout — VEX is an imperial system and modelling in inches keeps every number a
round, checkable figure. `+X` is the robot's right, `+Y` its front, `+Z` up, origin at the
centre of the drivebase footprint on the floor.

## Tuning it to the real robot

Everything lives in the `SPEC` object at the top of `lib/robot.js`. Measure the real robot
and change the numbers; the assembly, the BOM and the checks all follow. A few examples:

| You measured | Change |
|---|---|
| Wider or narrower chassis | `drive.outerRailX`, `frame.crossLenHoles` |
| 84T idlers instead of 60T | `drive.gearTeeth: 84` — station spacing must become 3.5" |
| A different tower angle | `tower.leanDeg` |
| Green (200 rpm) cartridges | `drive.cartridge: 'green'` |
| More or fewer chain flights | `tower.flightEvery` |

After any change, run `npm run check` — it will tell you if the new numbers break a mesh or
push the robot out of the cube.

## Assumptions

This was modelled from three photographs, not from measurements, so some of it is a
reading of the build rather than a record of it. The things most worth checking against the
real robot:

- **Gear sizes.** The drive idlers are modelled as 60T and the tower reduction as 84T,
  judged from their size relative to the 4" wheels. If the drive idlers are actually 84T,
  the station spacing has to go to 3.5" and the wheelbase grows with it.
- **Wheel types.** The corner wheels are modelled as 4" omnis. They are gear-linked to the
  rest of their side, which rules out mecanum — mecanum needs each wheel driven
  independently. If they really are mecanum, the gear train has to go.
- **The front intake.** The photos show structure low at the front of the tower; it is
  modelled as flex wheels sharing the lower conveyor shaft. The real mechanism may differ.
- **Motor count and placement.** Five V5 motors (4 drive, 1 conveyor) is inferred, not counted.
- **Off-grid shafts.** The tower, brace and arm lengths are rounded to whole hole counts,
  so their end shafts sit a few hundredths off the nominal points. The drivetrain is fully
  on-grid — all five stations and the motor mounts land on real holes.

## Output formats

`npm run export` writes STL (binary, whole robot and per subsystem) and, with `--obj`, OBJ.
There is no STEP export — that needs a real B-rep kernel, which this does not have. STL and
OBJ import fine into Onshape, Fusion and Blender as reference geometry.
