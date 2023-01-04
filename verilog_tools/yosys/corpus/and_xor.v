module and_not(a, b, out);

input  a, b;
output out;

assign out = a & (~b);

endmodule

module top(a, b, c, d, out);

input a, b, c, d;
output out;

wire w1, w2;
and_not m0(a, b, w1);
and_not m1(c, d, w2);
and_not m2(w1, w2, out);


endmodule