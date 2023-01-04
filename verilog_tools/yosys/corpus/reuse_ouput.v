module reuse_bits(out, in);
    input  [3:0] in;
    output [3:0] out;

    assign out[3] = in[3];
    assign out[2] = out[3];
    assign out[1] = !out[2];
    assign out[0] = out[2] & out[1];

endmodule

module invert_bits(out, in);
    input  [3:0] in;
    output [3:0] out;

    wire   [3:0] w1;
    reuse_bits r0(w1, in);

    assign out[3] = w1[3];
    assign out[2] = w1[1];
    assign out[1] = !w1[2];
    assign out[0] = !w1[0];

endmodule

module top(out, in);
    input  [3:0] in;
    output       out;

    wire   [3:0] w1;
    invert_bits invert0(w1, in);

    assign out = &w1;

endmodule
