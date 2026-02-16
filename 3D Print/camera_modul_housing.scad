// Library is loaded from the "lib" subfolder
use <lib/threads.scad>

/* [Selection] */
part_to_render = "cap"; // [base, cap]

/* [Top Feature Settings] */
top_feature_type = "thread"; // [none, hole, thread]
top_hole_diameter = 5.0; 
top_thread_size = "M12"; // [M10, M12, M14, M16]

/* [Internal Standoff Dimensions (Rectangular)] */
standoff_dist_x = 32.9;
standoff_dist_y = 32.9;
standoff_dia = 4.0;
standoff_hole_dia = 1.8;
standoff_height = 1.0;

/* [Base Settings] */
// Internal thread type (Note: 68x1 is larger than the default 64mm outer body!)
internal_thread_type = "42x0.75"; // [42x1, 42x0.75, 48x0.75, 54x0.75, 63x1, 68x1]
requested_thread_depth = 5.0; 
inner_chamfer_val = 0.75;
outer_chamfer = 1.5;

/* [Performance & Quality Tuning] */
final_fn = 500; 
final_resolution = 0.1; 
res = $preview ? 0.8 : final_resolution;

/* [General Settings] */
printer_tolerance = 0.4; 
$fn = $preview ? 32 : final_fn; 

/* [Shared Dimensions] */
outer_dia = 64;
outer_pitch = 2.0; 
total_height = 10.0; 

/* [Cap Settings] */
additional_space_input = 15; 
cap_wall_thickness = 3.0;
cap_top_thickness = 5.0; 
cap_outer_chamfer = 3.0; 

/* [Internal Geometry] */
square_size = 9.0;
square_chamfer_width = 1.0;

// --- Calculations ---
actual_additional_space = max(additional_space_input, 15);
cap_internal_bore = outer_dia - (1.0825 * outer_pitch); 
cap_outer_dia = outer_dia + (2 * cap_wall_thickness);
cap_total_height = total_height + actual_additional_space + cap_top_thickness;

top_thread_dia = (top_thread_size == "M10") ? 10 : (top_thread_size == "M12") ? 12 : (top_thread_size == "M14") ? 14 : 16;
top_thread_pitch = (top_thread_size == "M10") ? 1.5 : (top_thread_size == "M12") ? 1.75 : 2.0;

// UPDATED Internal Thread Logic Mapping
i_d_base = (internal_thread_type == "42x1" || internal_thread_type == "42x0.75") ? 42 : 
           (internal_thread_type == "48x0.75" ? 48 : 
           (internal_thread_type == "54x0.75" ? 54 : 
           (internal_thread_type == "63x1" ? 63 : 68)));

i_pitch = (internal_thread_type == "42x1" || internal_thread_type == "63x1" || internal_thread_type == "68x1") ? 1.0 : 0.75;

// --- Rendering Logic ---
if (part_to_render == "base") {
    render_base();
} else if (part_to_render == "cap") {
    translate([0, 0, cap_total_height])
    rotate([180, 0, 0])
    render_cap();
}

// --- Modules ---

module render_base() {
    actual_thread_depth = min(requested_thread_depth, total_height - 2);

    ScrewHole(i_d_base, actual_thread_depth, position=[0,0,-0.1], pitch=i_pitch, tolerance=printer_tolerance) {
        difference() {
            union() {
                ScrewThread(outer_dia, total_height, pitch=outer_pitch, tolerance=printer_tolerance);
                for(x = [-1, 1], y = [-1, 1]) {
                    translate([x * standoff_dist_x / 2, y * standoff_dist_y / 2, total_height])
                    cylinder(d = standoff_dia, h = standoff_height);
                }
            }
            translate([0, 0, -0.1])
                cylinder(d1 = i_d_base + (inner_chamfer_val * 2) + printer_tolerance, d2 = i_d_base + printer_tolerance, h = inner_chamfer_val + 0.1);
            
            cutout_h = total_height + standoff_height + 5;
            translate([0, 0, actual_thread_depth + (cutout_h / 2)])
                cube([square_size, square_size, cutout_h], center = true);
            
            translate([0, 0, actual_thread_depth - 0.1])
                rotate([0, 0, 45]) 
                cylinder(d1 = (square_size + 2 * square_chamfer_width) / cos(45), d2 = square_size / cos(45), h = square_chamfer_width + 0.1, $fn = 4);
            
            for(x = [-1, 1], y = [-1, 1]) {
                translate([x * standoff_dist_x / 2, y * standoff_dist_y / 2, total_height - 2])
                cylinder(d = standoff_hole_dia, h = 5);
            }
            
            difference() {
                translate([0, 0, total_height - outer_chamfer]) 
                    cylinder(d = outer_dia + 5, h = outer_chamfer + 0.2);
                translate([0, 0, total_height - outer_chamfer - 0.1]) 
                    cylinder(d1 = outer_dia + 1, d2 = outer_dia - (outer_chamfer * 2), h = outer_chamfer + 0.3);
            }
        }
    }
}

module render_cap() {
    difference() {
        cylinder(d = cap_outer_dia, h = cap_total_height);
        translate([0, 0, -0.1])
            ScrewThread(outer_dia + printer_tolerance, total_height + 0.1, pitch=outer_pitch);
        translate([0, 0, -0.1])
            cylinder(d = cap_internal_bore, h = total_height + actual_additional_space + 0.1);
        difference() {
            translate([0, 0, cap_total_height - cap_outer_chamfer]) 
                cylinder(d = cap_outer_dia + 5, h = cap_outer_chamfer + 0.1);
            translate([0, 0, cap_total_height - cap_outer_chamfer - 0.1]) 
                cylinder(d1 = cap_outer_dia + 0.1, d2 = cap_outer_dia - (cap_outer_chamfer * 2), h = cap_outer_chamfer + 0.2);
        }
        if (top_feature_type == "hole") {
            translate([0, 0, cap_total_height - cap_top_thickness - 0.1])
                cylinder(d = top_hole_diameter, h = cap_top_thickness + 0.2);
        } else if (top_feature_type == "thread") {
            translate([0, 0, cap_total_height - cap_top_thickness - 0.1])
                ScrewThread(top_thread_dia + printer_tolerance, cap_top_thickness + 0.2, pitch = top_thread_pitch);
            translate([0, 0, cap_total_height - cap_top_thickness - 0.2])
                cylinder(d = top_thread_dia - (1.0825 * top_thread_pitch), h = cap_top_thickness + 0.4);
        }
    }
}