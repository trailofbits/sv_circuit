module is_zero(out, in);
    input [3:0] in;
    output out;

    assign out = !(|in);

endmodule

module is_less_than_two(out, in);
    input [3:0] in;
    output out;

    wire w1;
    is_zero iz(w1, in);

    assign out = w1 || (in == 4'b0001);

endmodule

module top(out, in);
    input  [3:0] in;
    output       out;

    wire w1;
    is_less_than_two il(w1, in);

    assign out = !w1;

endmodule
