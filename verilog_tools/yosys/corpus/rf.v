module decoder2 (out, in, enable);
    input     in;
    input     enable;
    output [1:0] out;
 
    and a0(out[0], enable, ~in);
    and a1(out[1], enable, in);
endmodule // decoder2

module decoder4 (out, in, enable);
    input [1:0]    in;
    input     enable;
    output [3:0]   out;
    wire [1:0]    w_enable;

    decoder2 top(out[1:0], in[0], w_enable[0]);
    decoder2 bottom(out[3:2], in[0], w_enable[1]);
    decoder2 middle(w_enable, in[1], enable);
endmodule // decoder4

module decoder8 (out, in, enable);
    input [2:0]    in;
    input     enable;
    output [7:0]   out;
    wire [1:0]    w_enable;
 
    decoder4 top(out[3:0], in[1:0], w_enable[0]);
    decoder4 bottom(out[7:4], in[1:0], w_enable[1]);
    decoder2 middle(w_enable, in[2], enable);
endmodule // decoder8

module decoder16 (out, in, enable);
    input [3:0]    in;
    input     enable;
    output [15:0]  out;
    wire [1:0]    w_enable;
 
    decoder8 top(out[7:0], in[2:0], w_enable[0]);
    decoder8 bottom(out[15:8], in[2:0], w_enable[1]);
    decoder2 middle(w_enable, in[3], enable);
endmodule

module mux2v(out, A, B, sel);

    parameter
        width = 32;
    
    output [width-1:0] out;
    input  [width-1:0] A, B;
    input          sel;

    wire [width-1:0] temp1 = ({width{(!sel)}} & A);
    wire [width-1:0] temp2 = ({width{(sel)}} & B);
    assign out = temp1 | temp2;

endmodule // mux2v

module mux16v(out, A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, sel);

    parameter
        width = 32;
    
    output [width-1:0] out;
    input [width-1:0]  A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P;
    input [3:0]        sel;

    wire [width-1:0]   wAB, wCD, wEF, wGH, wIJ, wKL, wMN, wOP;
    wire [width-1:0]   wABCD, wEFGH, wIJKL, wMNOP;
    wire [width-1:0]   wABCDEFGH, wIJKLMNOP;
    
    mux2v #(width)  mAB (wAB, A, B, sel[0]);
    mux2v #(width)  mCD (wCD, C, D, sel[0]);
    mux2v #(width)  mEF (wEF, E, F, sel[0]);
    mux2v #(width)  mGH (wGH, G, H, sel[0]);
    mux2v #(width)  mIJ (wIJ, I, J, sel[0]);
    mux2v #(width)  mKL (wKL, K, L, sel[0]);
    mux2v #(width)  mMN (wMN, M, N, sel[0]);
    mux2v #(width)  mOP (wOP, O, P, sel[0]);

    mux2v #(width)  mABCD (wABCD, wAB, wCD, sel[1]);
    mux2v #(width)  mEFGH (wEFGH, wEF, wGH, sel[1]);
    mux2v #(width)  mIJKL (wIJKL, wIJ, wKL, sel[1]);
    mux2v #(width)  mMNOP (wMNOP, wMN, wOP, sel[1]);

    mux2v #(width)  mABCDEFGH (wABCDEFGH, wABCD, wEFGH, sel[2]);
    mux2v #(width)  mIJKLMNOP (wIJKLMNOP, wIJKL, wMNOP, sel[2]);
    
    mux2v #(width)  mfinal (out, wABCDEFGH, wIJKLMNOP, sel[3]);

endmodule // mux16v

// register: A register which may be reset to an arbirary value
//
// q      (output) - Current value of register
// d      (input)  - Next value of register
// clk    (input)  - Clock (positive edge-sensitive)
// enable (input)  - Load new value? (yes = 1, no = 0)
// reset  (input)  - Asynchronous reset    (reset = 1)
//
module register(q, d, clk, enable, reset);

    parameter
        width = 16,
        reset_value = 0;

    output [(width-1):0] q;
    reg    [(width-1):0] q;
    input  [(width-1):0] d;
    input  clk, enable, reset;

    always @(reset)
        if (reset == 1'b1)
            q <= reset_value;

    always @(posedge clk)
        if ((reset == 1'b0) && (enable == 1'b1))
            q <= d;

endmodule // register


module msp430_regfile_integrated_decoder (rd_data, 
                       rd_regnum, wr_regnum, wr_data,
                       write_enable, clock, reset);

    output [15:0]  rd_data;
    input   [4:0]  rd_regnum, wr_regnum;
    input  [15:0]  wr_data;
    input          write_enable, clock, reset;

    wire [15:0] enable_bus;

    wire [15:0] wire0, wire1, wire2, wire3, wire4, wire5, wire6, wire7, wire8;
    wire [15:0] wire9, wire10, wire11, wire12, wire13, wire14, wire15;

    decoder16 write_add(enable_bus, wr_regnum, write_enable);

    register reg0(wire0, wr_data, clock, enable_bus[0], reset);
    register reg1(wire1, wr_data, clock, enable_bus[1], reset);
    register reg2(wire2, wr_data, clock, enable_bus[2], reset);
    register reg3(wire3, wr_data, clock, enable_bus[3], reset);
    register reg4(wire4, wr_data, clock, enable_bus[4], reset);
    register reg5(wire5, wr_data, clock, enable_bus[5], reset);
    register reg6(wire6, wr_data, clock, enable_bus[6], reset);
    register reg7(wire7, wr_data, clock, enable_bus[7], reset);
    register reg8(wire8, wr_data, clock, enable_bus[8], reset);
    register reg9(wire9, wr_data, clock, enable_bus[9], reset);
    register reg10(wire10, wr_data, clock, enable_bus[10], reset);
    register reg11(wire11, wr_data, clock, enable_bus[11], reset);
    register reg12(wire12, wr_data, clock, enable_bus[12], reset);
    register reg13(wire13, wr_data, clock, enable_bus[13], reset);
    register reg14(wire14, wr_data, clock, enable_bus[14], reset);
    register reg15(wire15, wr_data, clock, enable_bus[15], reset);

    mux16v out(rd_data, wire0, wire1, wire2, wire3, wire4, wire5, wire6, wire7, wire8, wire9, wire10, wire11, wire12, wire13, wire14, wire15, rd_regnum);
    
endmodule // msp430_regfile


module msp430_regfile_mask_input (rd_data, 
                       rd_regnum_bit_0, rd_regnum_bit_1, rd_regnum_bit_2, rd_regnum_bit_3,
                       rd_regnum_bit_4, rd_regnum_bit_5, rd_regnum_bit_6, rd_regnum_bit_7,
                       rd_regnum_bit_8, rd_regnum_bit_9, rd_regnum_bit_10, rd_regnum_bit_11,
                       rd_regnum_bit_12, rd_regnum_bit_13, rd_regnum_bit_14, rd_regnum_bit_15,

                       wr_regnum_bit_0, wr_regnum_bit_1, wr_regnum_bit_2, wr_regnum_bit_3,
                       wr_regnum_bit_4, wr_regnum_bit_5, wr_regnum_bit_6, wr_regnum_bit_7,
                       wr_regnum_bit_8, wr_regnum_bit_9, wr_regnum_bit_10, wr_regnum_bit_11,
                       wr_regnum_bit_12, wr_regnum_bit_13, wr_regnum_bit_14, wr_regnum_bit_15,
                       wr_data,
                       write_enable, clock, reset);

    output [15:0]  rd_data;

    input rd_regnum_bit_0, rd_regnum_bit_1, rd_regnum_bit_2, rd_regnum_bit_3; 
    input rd_regnum_bit_4, rd_regnum_bit_5, rd_regnum_bit_6, rd_regnum_bit_7;
    input rd_regnum_bit_8, rd_regnum_bit_9, rd_regnum_bit_10, rd_regnum_bit_11;
    input rd_regnum_bit_12, rd_regnum_bit_13, rd_regnum_bit_14, rd_regnum_bit_15;

    input wr_regnum_bit_0, wr_regnum_bit_1, wr_regnum_bit_2, wr_regnum_bit_3; 
    input wr_regnum_bit_4, wr_regnum_bit_5, wr_regnum_bit_6, wr_regnum_bit_7;
    input wr_regnum_bit_8, wr_regnum_bit_9, wr_regnum_bit_10, wr_regnum_bit_11;
    input wr_regnum_bit_12, wr_regnum_bit_13, wr_regnum_bit_14, wr_regnum_bit_15;
    input  [15:0]  wr_data;
    input          write_enable, clock, reset;

    wire [15:0] wire0, wire1, wire2, wire3, wire4, wire5, wire6, wire7, wire8;
    wire [15:0] wire9, wire10, wire11, wire12, wire13, wire14, wire15;

    wire [15:0] out0, out1, out2, out3, out4, out5, out6, out7, out8;
    wire [15:0] out9, out10, out11, out12, out13, out14, out15;

    register reg0(wire0, wr_data, clock, wr_regnum_bit_0, reset);
    register reg1(wire1, wr_data, clock, wr_regnum_bit_1, reset);
    register reg2(wire2, wr_data, clock, wr_regnum_bit_2, reset);
    register reg3(wire3, wr_data, clock, wr_regnum_bit_3, reset);
    register reg4(wire4, wr_data, clock, wr_regnum_bit_4, reset);
    register reg5(wire5, wr_data, clock, wr_regnum_bit_5, reset);
    register reg6(wire6, wr_data, clock, wr_regnum_bit_6, reset);
    register reg7(wire7, wr_data, clock, wr_regnum_bit_7, reset);
    register reg8(wire8, wr_data, clock, wr_regnum_bit_8, reset);
    register reg9(wire9, wr_data, clock, wr_regnum_bit_9, reset);
    register reg10(wire10, wr_data, clock, wr_regnum_bit_10, reset);
    register reg11(wire11, wr_data, clock, wr_regnum_bit_11, reset);
    register reg12(wire12, wr_data, clock, wr_regnum_bit_12, reset);
    register reg13(wire13, wr_data, clock, wr_regnum_bit_13, reset);
    register reg14(wire14, wr_data, clock, wr_regnum_bit_14, reset);
    register reg15(wire15, wr_data, clock, wr_regnum_bit_15, reset);


    and(out0, wire0, {16{rd_regnum_bit_0}});
    and(out1, wire1, {16{rd_regnum_bit_1}});
    and(out2, wire2, {16{rd_regnum_bit_2}});
    and(out3, wire3, {16{rd_regnum_bit_3}});
    and(out4, wire4, {16{rd_regnum_bit_4}});
    and(out5, wire5, {16{rd_regnum_bit_5}});
    and(out6, wire6, {16{rd_regnum_bit_6}});
    and(out7, wire7, {16{rd_regnum_bit_7}});
    and(out8, wire8, {16{rd_regnum_bit_8}});
    and(out9, wire9, {16{rd_regnum_bit_9}});
    and(out10, wire10, {16{rd_regnum_bit_10}});
    and(out11, wire11, {16{rd_regnum_bit_11}});
    and(out12, wire12, {16{rd_regnum_bit_12}});
    and(out13, wire13, {16{rd_regnum_bit_13}});
    and(out14, wire14, {16{rd_regnum_bit_14}});
    and(out15, wire15, {16{rd_regnum_bit_15}});


    or(rd_data, out0, out1, out2, out3, out4, out5, out6, out7,
       out8, out9, out10, out11, out12, out13, out14, out15);
    
endmodule // msp430_regfile



////////////////////////////////////////////////////////////////////////
//
// Module: regfile
//
// Description:
//   A behavioral MIPS register file.  R0 is hardwired to zero.
//   Given that you won't write behavioral code, don't worry if you don't
//   understand how this works;  We have to use behavioral code (as 
//   opposed to the structural code you are writing), because of the 
//   latching by the the register file.
//
// module regfile (rData,
//                 rsNum, rtNum, rdNum, rdData, 
//                 rdWriteEnable, clock, reset);

//     output [15:0] rData;
//     input   [3:0] rsNum, rtNum, rdNum;
//     input  [15:0] rdData;
//     input         rdWriteEnable, clock, reset;
    
//     reg signed [15:0] r [0:15];
//     integer i;

//     always @(reset)
//         if (reset == 1'b1)
//         begin
//             for(i = 0; i <= 15; i = i + 1)
//                 r[i] <= 0;
//         end

//     assign rsData = r[rsNum];
//     assign rtData = r[rtNum];

//     always @(posedge clock)
//     begin
//         if ((reset == 1'b0) && (rdWriteEnable == 1'b1) && (rdNum != 5'b0))
//             r[rdNum] <= rdData;
//     end

// endmodule // regfile
