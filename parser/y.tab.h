/* A Bison parser, made by GNU Bison 2.3.  */

/* Skeleton interface for Bison's Yacc-like parsers in C

   Copyright (C) 1984, 1989, 1990, 2000, 2001, 2002, 2003, 2004, 2005, 2006
   Free Software Foundation, Inc.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin Street, Fifth Floor,
   Boston, MA 02110-1301, USA.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* Tokens.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
   /* Put the tokens into the symbol table, so that GDB and other debuggers
      know about them.  */
   enum yytokentype {
     IDENTIFIER = 258,
     INT_LITERAL = 259,
     FLOAT_LITERAL = 260,
     STRING_LITERAL = 261,
     SELECT = 262,
     FROM = 263,
     WHERE = 264,
     JOIN = 265,
     ON = 266,
     AS = 267,
     AND = 268,
     OR = 269,
     NOT = 270,
     GROUP = 271,
     BY = 272,
     HAVING = 273,
     EQ = 274,
     LT = 275,
     GT = 276,
     LEQ = 277,
     GEQ = 278,
     NEQ = 279
   };
#endif
/* Tokens.  */
#define IDENTIFIER 258
#define INT_LITERAL 259
#define FLOAT_LITERAL 260
#define STRING_LITERAL 261
#define SELECT 262
#define FROM 263
#define WHERE 264
#define JOIN 265
#define ON 266
#define AS 267
#define AND 268
#define OR 269
#define NOT 270
#define GROUP 271
#define BY 272
#define HAVING 273
#define EQ 274
#define LT 275
#define GT 276
#define LEQ 277
#define GEQ 278
#define NEQ 279




#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
typedef union YYSTYPE
#line 131 "sql_parser.y"
{
    int intval;
    float floatval;
    char *strval;
    struct Column *col;
    struct Table *tbl;
    struct Condition *cond;
    struct RelNode *node;
}
/* Line 1529 of yacc.c.  */
#line 107 "y.tab.h"
	YYSTYPE;
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
# define YYSTYPE_IS_TRIVIAL 1
#endif

extern YYSTYPE yylval;

