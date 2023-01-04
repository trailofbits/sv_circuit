module const_check(in, verifies);

input  [4:0] in;
output       verifies;

assign verifies = (in == 5'b10111);

endmodule

module top(in, verifies);

input  [2:0] in;
output       verifies;

const_check c0(
  .verifies(verifies),
  .in({1'b1, in, 1'b1})
);

endmodule
