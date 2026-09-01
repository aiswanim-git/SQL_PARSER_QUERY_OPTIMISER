%{
// Include the bison-generated header for token definitions and YYSTYPE
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "y.tab.h"

// SQL query schema supported:
// SELECT <select_list>
// FROM <table_or_join>
// [WHERE <condition>]
// [GROUP BY <grouping_columns>]
// [HAVING <group_condition>]
%}

DIGIT      [0-9]
LETTER     [a-zA-Z_]
ID         {LETTER}({LETTER}|{DIGIT})*
INT        {DIGIT}+
FLOAT      {DIGIT}+\.{DIGIT}+
STRING     \'[^\']*\'
WS         [ \t\n\r]+

%%

SELECT      { return SELECT; }
FROM        { return FROM; }
WHERE       { return WHERE; }
JOIN        { return JOIN; }
ON          { return ON; }
GROUP       { return GROUP; }
BY          { return BY; }
AS          { return AS; }
AND         { return AND; }
OR          { return OR; }
NOT         { return NOT; }
HAVING      { return HAVING; }

"<="        { return LEQ; }
">="        { return GEQ; }
"<>"        { return NEQ; }
"="         { return EQ; }
">"         { return GT; }
"<"         { return LT; }

","         { return ','; }
"."         { return '.'; }
"("         { return '('; }
")"         { return ')'; }
"*"         { return '*'; }

{FLOAT} {
    yylval.floatval = atof(yytext);
    return FLOAT_LITERAL;
}

{INT} {
    yylval.intval = atoi(yytext);
    return INT_LITERAL;
}

{STRING} {
    //Step 1: Strip surrounding single quotes from string literal
    yytext[yyleng - 1] = '\0';
    yylval.strval = strdup(yytext + 1);
    return STRING_LITERAL;
}

{ID} {
    yylval.strval = strdup(yytext);
    return IDENTIFIER;
}

{WS}   { /* skip whitespace */ }

. {
    fprintf(stderr, "Invalid character: %s\n", yytext);
}

%%

int yywrap() {
    return 1;
}