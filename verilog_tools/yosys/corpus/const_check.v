module const_check(in, verifies);

input  [31:0] in;
output        verifies;

assign verifies = (in == 32'hDEADBEEF);

endmodule
