module inner(in, out);

input  [2:0] in;
output       out;

assign out = in[2] & (in[1] ^ in[0]);

endmodule

module top(in, out);

input  [8:0] in;
output       out;

wire   [2:0] c0, c1, c2;
assign {c0, c1, c2} = in;

wire   [2:0] iw;

inner i0(
    .in(c0),
    .out(iw[0])
);

inner i1(
    .in(c1),
    .out(iw[1])
);

inner i2(
    .in(c2),
    .out(iw[2])
);

inner i_final(
    .in(iw),
    .out(out)
);

endmodule
