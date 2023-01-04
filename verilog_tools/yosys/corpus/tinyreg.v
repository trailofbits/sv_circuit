module register(q, d, clock);

    parameter
        width = 8;

    output [(width-1):0] q;
    reg    [(width-1):0] q;
    input  [(width-1):0] d;
    input  clock;

    always @(posedge clock)
        // if (enable == 1'b1)
            q <= d;

endmodule // register