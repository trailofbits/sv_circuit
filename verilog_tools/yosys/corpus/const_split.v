module const_check(in1, in2, in3, in4, verifies);

input  [7:0] in1, in2, in3, in4;
output        verifies;

assign verifies = (in1 == 8'hDE) && (in2 == 8'hAD) && (in3 == 8'hBE) && (in4 == 8'hEF);

endmodule
