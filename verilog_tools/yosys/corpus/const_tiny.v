module const_check(in, verifies);

input  [2:0] in;
output       verifies;

assign verifies = (in == 3'b011);

endmodule
