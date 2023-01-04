module implicit_branch(i, bf, verifies);

input  [2:0] bf;
input        i;
output       verifies;

assign verifies = (i == bf[0]) && (i == bf[1]) && (i == bf[2]);

endmodule
