all: build

build:
	bison -d -o y.tab.c sql_parser.y
	flex -o lex.yy.c sql_tokeniser.l
	g++ -o sql_parser y.tab.c lex.yy.c 

clean:
	rm -f sql_parser y.tab.c y.tab.h lex.yy.c
