reverie-companion --operation prove --program-format bristol --program-path $1 --proof-path $1.out --witness-path $2 > /dev/null && reverie-companion --operation verify --program-format bristol --program-path $1 --proof-path $1.out
rm $1.out
