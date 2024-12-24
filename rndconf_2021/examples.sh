echo -e "\033[1;41m Fatal \033[0m" \
        "\033[7;31m Critical \033[0m" \
        "\033[1;31m Error \033[0m" \
        "\033[0;31m Warning \033[0m" \
        "\033[0;33m Notice \033[0m" \
        "\033[1m Information \033[0m" \
        " Debug " \
        "\033[2m Trace \033[0m"


for i in {0..1}; do for j in {0..7}; do echo -e "\033[${i};3${j}m ☻☺☻☺☻☺☻☺☻☺☻☺☻☺☻☺☻☺☻☺ \033[0m "; done; echo; done


COLORS=("\033[0;31m" "\033[0;32m" "\033[0;33m" "\033[0;34m" "\033[0;35m"
        "\033[0;36m" "\033[0;37m" "\033[1;30m" "\033[1;31m" "\033[1;32m"
        "\033[1;34m" "\033[1;35m" "\033[1;36m");
NOCOLOR="\033[0m"; 

for i in {0..1000}; 
do
    COLOR=${COLORS[$(($RANDOM % ${#COLORS[*]}))]}; 
    echo -n -e $COLOR test $NOCOLOR; 
done
