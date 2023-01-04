module switch2(out, in, control);
    output [1:0] out;
    input  [1:0] in;
    input  control;
         
    assign out = control ? {in[0], in[1]} : {in[1], in[0]};
endmodule // switch2

module switch4(out, in, control);
    output [3:0] out;
    input  [3:0] in;
    input  [5:0] control;
         
    wire l0, l1, l2, l3;
    wire r0, r1, r2, r3;

    switch2 left1({l0, l1}, in[1:0], control[0]);
    switch2 left2({l2, l3}, in[3:2], control[1]);

    switch2 mid1({r0, r1}, {l0, l2}, control[2]);
    switch2 mid2({r2, r3}, {l1, l3}, control[3]);

    switch2 right1(out[0:1], {r0, r2}, control[4]);
    switch2 right2(out[3:2], {r1, r3}, control[5]);

endmodule // switch4

module switch8(out, in, control);
    output [7:0] out;
    input  [7:0] in;
    input  [19:0] control;
         
    wire l0, l1, l2, l3, l4, l5, l6, l7;
    wire r0, r1, r2, r3, r4, r5, r6, r7;

    switch2 left1({l0, l1}, in[1:0], control[0]);
    switch2 left2({l2, l3}, in[3:2], control[1]);
    switch2 left3({l4, l5}, in[5:4], control[2]);
    switch2 left4({l6, l7}, in[7:6], control[3]);

    switch4 mid1({r0, r1, r2, r3}, {l0, l2, l4, l6}, control[9:4]);
    switch4 mid2({r4, r5, r6, r7}, {l1, l3, l5, l7}, control[15:10]);

    switch2 right1(out[1:0], {r0, r4}, control[16]);
    switch2 right2(out[3:2], {r1, r5}, control[17]);
    switch2 right3(out[5:4], {r2, r6}, control[18]);
    switch2 right4(out[7:6], {r3, r7}, control[19]);

endmodule // switch8

module switchn(out, in, control);
    parameter
        width = 8;

    localparam nbits = width * $clog2(width) - width/2;
    localparam nbits_half = width/2 * $clog2(width/2) - width/4;
    output [width - 1:0] out;
    input  [width - 1:0] in;
    input  [(nbits-1):0] control;

    generate
    if (width == 2)
        begin
            assign out = control ? {in[0], in[1]} : {in[1], in[0]};
        end
    else
        begin
            wire [width-1:0] l;
            wire [width-1:0] r;
            
            genvar i;
            for (i = 0; i < width/2; i = i + 1) begin
                switchn #(2) left({l[i*2], l[i*2+1]}, in[i*2+1:i*2], control[i]);
            end

            wire [(width/2)-1:0] l1;
            wire [(width/2)-1:0] l2;

            for (i = 0; i < width/2; i = i + 1) begin
                assign l1[i] = l[2*i];
                assign l2[i] = l[2*i+1];
            end

            switchn #(width/2) mid1(r[width/2-1:0],       l1, control[width/2 + nbits_half - 1:width/2]);
            switchn #(width/2) mid2(r[width-1:width/2],   l2, control[width/2+2*nbits_half-1:width/2+nbits_half]);

            for (i = 0; i < width/2; i = i + 1) begin
                switchn #(2) right(out[i*2+1:i*2], {r[i], r[width/2+i]}, control[nbits - width/2 + i]);
            end
        end
    endgenerate

endmodule // switchn

module xorshift32(out, in);
    output [31:0] out;
    input  [31:0] in;
         
    assign out = (in << 13) ^ (in >> 17) ^ (in << 5);
endmodule // xorshift32

module xorshift64(out, in);
    output [63:0] out;
    input  [63:0] in;
         
    assign out = (in << 13) ^ (in >> 7) ^ (in << 17);
endmodule // xorshift64


