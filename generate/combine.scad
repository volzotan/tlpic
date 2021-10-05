union() {
    intersection() {
        rotate([-90, 0, 0]) 
        translate([0, -10, 0])
        //import("SLP3_intersect.stl");
        union() {
            import("Frontplate.stl");
            import("SLP3_combine.stl");
        };

        translate([0, 0, 10]) 
        import("p.stl");
    };
    intersection() {
        rotate([-90, 0, 0]) 
        translate([0, -10, 0])
        import("SLP3_combine.stl"); 
        translate([0, 0, 0.1])cube([60, 110, 10]);
    };
}

