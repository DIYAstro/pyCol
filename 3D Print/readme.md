# Threaded Enclosure System

OpenSCAD project for a threaded enclosure system, designed to house **USB camera modules**. It consists of a **Base** and a matching **Cap**. 

## Performance Note

For performance reasons, it is recommended to use the [OpenSCAD Nightly (Development Snapshot)](https://openscad.org/downloads.html#snapshots). Rendering is significantly faster with the Manifold engine enabled.

---

## Features

### Base Module
* **External Thread:** Fixed M64x2.0.
* **Internal Interface:** Selectable options for M42, M48, M54, M63, and M68.
* **Standoffs:** 4x pillars in a rectangular grid (Default: 32.9mm x 32.9mm).
* **Center Pass-through:** 9mm square cutout.

### Cap Module
* **Printing Orientation:** The cap is rendered upside-down to avoid support structures.
* **Internal Cavity:** Threaded section (10mm) followed by an expansion bore.
* **Top Interface:** 
    * `thread`: Metric threads (M10-M16).
    * `hole`: Simple pass-through hole.
    * `none`: Solid lid.

---

## Parameters

| Variable | Description | Default |
| :--- | :--- | :--- |
| `part_to_render` | Toggle between 'base' and 'cap' | `cap` |
| `internal_thread_type` | Internal interface of the base | `42x0.75` |
| `standoff_dist_x/y` | Spacing for pillars | `32.9mm` |
| `printer_tolerance` | Clearance for 3D printed fit | `0.4mm` |
| `top_feature_type` | Lid interface type | `thread` |

---

## Technical Details

### Thread Calculations
The script uses the `threads.scad` library. Internal diameters are based on the ISO metric profile:

$D_{int} = D_{nom} - (1.0825 \times Pitch)$

### Tolerance Handling
`printer_tolerance` is added to internal threads to ensure fit on FDM printers. For SLA (Resin) prints, consider reducing this value.

---

## License & Credits
The `threads.scad` library in the `/lib` folder was created by **Ryan A. Colyer** and is released under the **CC0 1.0 Public Domain Dedication**. 

See [lib/LICENSE.md](lib/LICENSE.md) for details.
