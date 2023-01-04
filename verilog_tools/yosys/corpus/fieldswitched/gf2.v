module zk_stmt(out, in);

output [63:0] out;

input [7:0] in;

assign out = {56'h41414141, in};

endmodule
