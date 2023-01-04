module cmp_n(out, d1, d2);
    parameter
        width = 1;

    output  out;
    input  [width-1:0]  d1, d2;

    generate
    if (width == 1)
        begin
            assign out = (d1 == d2);
        end
    else
        begin
            wire w1, w2;

            cmp_n #(width/2) l(w1, d1[width-1:width/2], d2[width-1:width/2]);
            cmp_n #(width/2) r(w2, d1[(width/2-1):0], d2[(width/2-1):0]);

            and a0(out, w1, w2);
        end
    endgenerate
endmodule

module cmp128(out, d1, d2);
    output  out;
    input  [127:0]  d1, d2;
    cmp_n #(128) c0(out, d1, d2);
endmodule

