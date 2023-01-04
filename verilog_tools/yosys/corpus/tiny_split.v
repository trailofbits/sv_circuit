module wtf(i1, i2, out);

input [2:0] i1, i2;
output out;

assign out = (i1 == 3'b011) && (i2 == 3'b100);

endmodule
