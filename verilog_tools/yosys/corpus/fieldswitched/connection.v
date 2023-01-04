module top(out);

output out;

wire [63:0] bool_out;
wire        arith_in;

zk_stmt c0(
    .out(bool_out)
);

BToA con(
    .dst(arith_in),
    .src(bool_out)
);

zk_stmt_arith b0(
    .in(arith_in),
    .out(out)
);

endmodule