module big_reduce_and(out, in);
    parameter width = 8;

    output out;
    input [width-1:0] in;

    assign out = &in;

endmodule
