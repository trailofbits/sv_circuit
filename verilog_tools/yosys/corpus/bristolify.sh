
fname=$(basename $1 | cut -f 1 -d '.')

sv-netlist $fname.blif $1
sv-bristol $fname.blif -o $fname.bf
