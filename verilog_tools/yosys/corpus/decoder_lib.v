module decoder2(outA, outB, sel);

    parameter
        width = 1;
    
    output [width-1:0] outA, outB;
    input          sel;

    assign outA = (sel == 'b0);
    assign outB = (sel == 'b1);

endmodule // decoder2

module decoder4(outA, outB, outC, outD, sel);

    parameter
        width = 1;
    
    output [width-1:0] outA, outB, outC, outD;
    input  [1:0]       sel;
    
    assign outA = (sel == 'b00);
    assign outB = (sel == 'b01);
    assign outC = (sel == 'b10);
    assign outD = (sel == 'b11);

endmodule // decoder4

module decoder8(outA, outB, outC, outD, outE, outF, outG, outH, sel);

    parameter
        width = 1;
    
    output [width-1:0] outA, outB, outC, outD, outE, outF, outG, outH;
    input  [2:0]       sel;
    
    assign outA = (sel == 'b000);
    assign outB = (sel == 'b001);
    assign outC = (sel == 'b010);
    assign outD = (sel == 'b011);
    assign outE = (sel == 'b100);
    assign outF = (sel == 'b101);
    assign outG = (sel == 'b110);
    assign outH = (sel == 'b111);


endmodule // decoder8

