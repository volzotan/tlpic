union() {
    difference(){
        
        rotate([-90, 0, 0]) 
            translate([0, -10, 0])
                import("Frontplate.stl");
        
        rotate([-90, 0, 0]) 
            translate([0, -10, 0])
                import("SLP_allowed.stl"); 
    }
    intersection(){
        
        translate([0, 0, 10]) 
            import("p.stl");
        
        rotate([-90, 0, 0]) 
            translate([0, -10, 0])
                import("SLP_allowed.stl"); 
    }
}