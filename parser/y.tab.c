/* A Bison parser, made by GNU Bison 2.3.  */

/* Skeleton implementation for Bison's Yacc-like parsers in C

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

/* C LALR(1) parser skeleton written by Richard Stallman, by
   simplifying the original so-called "semantic" parser.  */

/* All symbols defined below should begin with yy or YY, to avoid
   infringing on user name space.  This should be done even for local
   variables, as they might otherwise be expanded by user macros.
   There are some unavoidable exceptions within include files to
   define necessary library symbols; they are noted "INFRINGES ON
   USER NAME SPACE" below.  */

/* Identify Bison output.  */
#define YYBISON 1

/* Bison version.  */
#define YYBISON_VERSION "2.3"

/* Skeleton name.  */
#define YYSKELETON_NAME "yacc.c"

/* Pure parsers.  */
#define YYPURE 0

/* Using locations.  */
#define YYLSP_NEEDED 0



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




/* Copy the first part of user declarations.  */
#line 1 "sql_parser.y"

#include <iostream>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using namespace std;

void yyerror(const char *s);
int yylex();
extern FILE *yyin;

//Step 1: Define operation and condition type enumerations
typedef enum {
    OP_PROJECT,
    OP_SELECT,
    OP_JOIN,
    OP_RENAME,
    OP_GROUPBY,
    OP_SUBQUERY
} RelOpType;

typedef enum {
    COND_EQ,
    COND_LT,
    COND_GT,
    COND_LE,
    COND_GE,
    COND_NE,
    COND_AND,
    COND_OR,
    COND_NOT
} CondType;

//Step 2: Define data structure types for columns, tables, conditions, and relational nodes
typedef struct Column {
    char *table;
    char *attr;
    struct Column *next;
} Column;

typedef struct Table {
    char *name;
    char *alias;
    struct Table *next;
} Table;

typedef struct Condition {
    CondType type;
    union {
        struct {
            struct Condition *left;
            struct Condition *right;
        } binary;
        struct {
            struct Condition *cond;
        } unary;
        struct {
            char *table;
            char *attr;
            int int_literal;
            float float_literal;
            char *str_literal;
            int literal_type; // 0: int, 1: float, 2: string, 3: column
            char *cmp_table;
            char *cmp_attr;
        } comparison;
    } expr;
} Condition;

typedef struct RelNode {
    RelOpType op_type;
    union {
        struct {
            struct RelNode *input;
            Column *columns;
        } project;
        struct {
            struct RelNode *input;
            Condition *condition;
        } select;
        struct {
            struct RelNode *left;
            struct RelNode *right;
            Condition *condition;
        } join;
        struct {
            struct RelNode *input;
            char *old_name;
            char *new_name;
        } rename;
        struct {
            struct RelNode *input;
            Column *group_cols;
            Condition *having_cond;
        } groupby;
        struct {
            struct RelNode *subquery;
            char *alias;
        } subquery;
    } op;
    Table *tables; // for base relations only
} RelNode;

//Step 3: Declare all helper functions
Column    *create_column(char *table, char *attr);
Column    *append_column(Column *list, Column *new_col);
Table     *create_table(char *name, char *alias);
Table     *append_table(Table *list, Table *new_table);
Condition *create_comparison(CondType type, char *table, char *attr,
                             int literal_type, int int_val, float float_val,
                             char *str_val, char *cmp_table, char *cmp_attr);
Condition *create_binary_condition(CondType type, Condition *left, Condition *right);
Condition *create_unary_condition(CondType type, Condition *cond);
RelNode   *create_project_node(RelNode *input, Column *columns);
RelNode   *create_select_node(RelNode *input, Condition *condition);
RelNode   *create_join_node(RelNode *left, RelNode *right, Condition *condition);
RelNode   *create_rename_node(RelNode *input, char *old_name, char *new_name);
RelNode   *create_groupby_node(RelNode *input, Column *group_cols, Condition *having_cond);
RelNode   *create_base_relation(Table *tables);
RelNode   *create_subquery_node(RelNode *subquery, char *alias);
void       print_ra_tree_json(RelNode *root);
void       free_columns(Column *cols);
void       free_tables(Table *tables);
void       free_condition(Condition *cond);
void       free_relnode(RelNode *node);

RelNode *result = NULL;


/* Enabling traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif

/* Enabling verbose error messages.  */
#ifdef YYERROR_VERBOSE
# undef YYERROR_VERBOSE
# define YYERROR_VERBOSE 1
#else
# define YYERROR_VERBOSE 0
#endif

/* Enabling the token table.  */
#ifndef YYTOKEN_TABLE
# define YYTOKEN_TABLE 0
#endif

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
/* Line 193 of yacc.c.  */
#line 284 "y.tab.c"
	YYSTYPE;
# define yystype YYSTYPE /* obsolescent; will be withdrawn */
# define YYSTYPE_IS_DECLARED 1
# define YYSTYPE_IS_TRIVIAL 1
#endif



/* Copy the second part of user declarations.  */


/* Line 216 of yacc.c.  */
#line 297 "y.tab.c"

#ifdef short
# undef short
#endif

#ifdef YYTYPE_UINT8
typedef YYTYPE_UINT8 yytype_uint8;
#else
typedef unsigned char yytype_uint8;
#endif

#ifdef YYTYPE_INT8
typedef YYTYPE_INT8 yytype_int8;
#elif (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
typedef signed char yytype_int8;
#else
typedef short int yytype_int8;
#endif

#ifdef YYTYPE_UINT16
typedef YYTYPE_UINT16 yytype_uint16;
#else
typedef unsigned short int yytype_uint16;
#endif

#ifdef YYTYPE_INT16
typedef YYTYPE_INT16 yytype_int16;
#else
typedef short int yytype_int16;
#endif

#ifndef YYSIZE_T
# ifdef __SIZE_TYPE__
#  define YYSIZE_T __SIZE_TYPE__
# elif defined size_t
#  define YYSIZE_T size_t
# elif ! defined YYSIZE_T && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
#  include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  define YYSIZE_T size_t
# else
#  define YYSIZE_T unsigned int
# endif
#endif

#define YYSIZE_MAXIMUM ((YYSIZE_T) -1)

#ifndef YY_
# if defined YYENABLE_NLS && YYENABLE_NLS
#  if ENABLE_NLS
#   include <libintl.h> /* INFRINGES ON USER NAME SPACE */
#   define YY_(msgid) dgettext ("bison-runtime", msgid)
#  endif
# endif
# ifndef YY_
#  define YY_(msgid) msgid
# endif
#endif

/* Suppress unused-variable warnings by "using" E.  */
#if ! defined lint || defined __GNUC__
# define YYUSE(e) ((void) (e))
#else
# define YYUSE(e) /* empty */
#endif

/* Identity function, used to suppress warnings about constant conditions.  */
#ifndef lint
# define YYID(n) (n)
#else
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static int
YYID (int i)
#else
static int
YYID (i)
    int i;
#endif
{
  return i;
}
#endif

#if ! defined yyoverflow || YYERROR_VERBOSE

/* The parser invokes alloca or malloc; define the necessary symbols.  */

# ifdef YYSTACK_USE_ALLOCA
#  if YYSTACK_USE_ALLOCA
#   ifdef __GNUC__
#    define YYSTACK_ALLOC __builtin_alloca
#   elif defined __BUILTIN_VA_ARG_INCR
#    include <alloca.h> /* INFRINGES ON USER NAME SPACE */
#   elif defined _AIX
#    define YYSTACK_ALLOC __alloca
#   elif defined _MSC_VER
#    include <malloc.h> /* INFRINGES ON USER NAME SPACE */
#    define alloca _alloca
#   else
#    define YYSTACK_ALLOC alloca
#    if ! defined _ALLOCA_H && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
#     include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#     ifndef _STDLIB_H
#      define _STDLIB_H 1
#     endif
#    endif
#   endif
#  endif
# endif

# ifdef YYSTACK_ALLOC
   /* Pacify GCC's `empty if-body' warning.  */
#  define YYSTACK_FREE(Ptr) do { /* empty */; } while (YYID (0))
#  ifndef YYSTACK_ALLOC_MAXIMUM
    /* The OS might guarantee only one guard page at the bottom of the stack,
       and a page size can be as small as 4096 bytes.  So we cannot safely
       invoke alloca (N) if N exceeds 4096.  Use a slightly smaller number
       to allow for a few compiler-allocated temporary stack slots.  */
#   define YYSTACK_ALLOC_MAXIMUM 4032 /* reasonable circa 2006 */
#  endif
# else
#  define YYSTACK_ALLOC YYMALLOC
#  define YYSTACK_FREE YYFREE
#  ifndef YYSTACK_ALLOC_MAXIMUM
#   define YYSTACK_ALLOC_MAXIMUM YYSIZE_MAXIMUM
#  endif
#  if (defined __cplusplus && ! defined _STDLIB_H \
       && ! ((defined YYMALLOC || defined malloc) \
	     && (defined YYFREE || defined free)))
#   include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#   ifndef _STDLIB_H
#    define _STDLIB_H 1
#   endif
#  endif
#  ifndef YYMALLOC
#   define YYMALLOC malloc
#   if ! defined malloc && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
void *malloc (YYSIZE_T); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
#  ifndef YYFREE
#   define YYFREE free
#   if ! defined free && ! defined _STDLIB_H && (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
void free (void *); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
# endif
#endif /* ! defined yyoverflow || YYERROR_VERBOSE */


#if (! defined yyoverflow \
     && (! defined __cplusplus \
	 || (defined YYSTYPE_IS_TRIVIAL && YYSTYPE_IS_TRIVIAL)))

/* A type that is properly aligned for any stack member.  */
union yyalloc
{
  yytype_int16 yyss;
  YYSTYPE yyvs;
  };

/* The size of the maximum gap between one aligned stack and the next.  */
# define YYSTACK_GAP_MAXIMUM (sizeof (union yyalloc) - 1)

/* The size of an array large to enough to hold all stacks, each with
   N elements.  */
# define YYSTACK_BYTES(N) \
     ((N) * (sizeof (yytype_int16) + sizeof (YYSTYPE)) \
      + YYSTACK_GAP_MAXIMUM)

/* Copy COUNT objects from FROM to TO.  The source and destination do
   not overlap.  */
# ifndef YYCOPY
#  if defined __GNUC__ && 1 < __GNUC__
#   define YYCOPY(To, From, Count) \
      __builtin_memcpy (To, From, (Count) * sizeof (*(From)))
#  else
#   define YYCOPY(To, From, Count)		\
      do					\
	{					\
	  YYSIZE_T yyi;				\
	  for (yyi = 0; yyi < (Count); yyi++)	\
	    (To)[yyi] = (From)[yyi];		\
	}					\
      while (YYID (0))
#  endif
# endif

/* Relocate STACK from its old location to the new one.  The
   local variables YYSIZE and YYSTACKSIZE give the old and new number of
   elements in the stack, and YYPTR gives the new location of the
   stack.  Advance YYPTR to a properly aligned location for the next
   stack.  */
# define YYSTACK_RELOCATE(Stack)					\
    do									\
      {									\
	YYSIZE_T yynewbytes;						\
	YYCOPY (&yyptr->Stack, Stack, yysize);				\
	Stack = &yyptr->Stack;						\
	yynewbytes = yystacksize * sizeof (*Stack) + YYSTACK_GAP_MAXIMUM; \
	yyptr += yynewbytes / sizeof (*yyptr);				\
      }									\
    while (YYID (0))

#endif

/* YYFINAL -- State number of the termination state.  */
#define YYFINAL  8
/* YYLAST -- Last index in YYTABLE.  */
#define YYLAST   99

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  30
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  19
/* YYNRULES -- Number of rules.  */
#define YYNRULES  59
/* YYNRULES -- Number of states.  */
#define YYNSTATES  107

/* YYTRANSLATE(YYLEX) -- Bison symbol number corresponding to YYLEX.  */
#define YYUNDEFTOK  2
#define YYMAXUTOK   279

#define YYTRANSLATE(YYX)						\
  ((unsigned int) (YYX) <= YYMAXUTOK ? yytranslate[YYX] : YYUNDEFTOK)

/* YYTRANSLATE[YYLEX] -- Bison symbol number corresponding to YYLEX.  */
static const yytype_uint8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
      28,    29,    27,     2,    25,     2,    26,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     1,     2,     3,     4,
       5,     6,     7,     8,     9,    10,    11,    12,    13,    14,
      15,    16,    17,    18,    19,    20,    21,    22,    23,    24
};

#if YYDEBUG
/* YYPRHS[YYN] -- Index of the first RHS symbol of rule number YYN in
   YYRHS.  */
static const yytype_uint16 yyprhs[] =
{
       0,     0,     3,     5,    13,    15,    19,    23,    27,    29,
      31,    35,    37,    43,    45,    47,    49,    55,    60,    62,
      66,    69,    70,    72,    75,    76,    80,    82,    86,    87,
      90,    92,    94,    98,   102,   105,   109,   117,   125,   133,
     141,   149,   157,   163,   169,   175,   181,   187,   193,   199,
     205,   211,   217,   223,   229,   235,   241,   247,   253,   259
};

/* YYRHS -- A `-1'-separated list of the rules' RHS.  */
static const yytype_int8 yyrhs[] =
{
      31,     0,    -1,    32,    -1,     7,    33,     8,    36,    41,
      43,    45,    -1,    34,    -1,    33,    25,    34,    -1,     3,
      26,    35,    -1,     3,    26,    27,    -1,    27,    -1,     3,
      -1,    35,    26,     3,    -1,    38,    -1,    36,    10,    37,
      11,    46,    -1,    38,    -1,    40,    -1,    39,    -1,    28,
      32,    29,    12,     3,    -1,    28,    32,    29,     3,    -1,
       3,    -1,     3,    12,     3,    -1,     3,     3,    -1,    -1,
      42,    -1,     9,    47,    -1,    -1,    16,    17,    44,    -1,
      34,    -1,    44,    25,    34,    -1,    -1,    18,    47,    -1,
      47,    -1,    48,    -1,    47,    13,    47,    -1,    47,    14,
      47,    -1,    15,    47,    -1,    28,    47,    29,    -1,     3,
      26,    35,    19,     3,    26,    35,    -1,     3,    26,    35,
      20,     3,    26,    35,    -1,     3,    26,    35,    21,     3,
      26,    35,    -1,     3,    26,    35,    22,     3,    26,    35,
      -1,     3,    26,    35,    23,     3,    26,    35,    -1,     3,
      26,    35,    24,     3,    26,    35,    -1,     3,    26,    35,
      19,     4,    -1,     3,    26,    35,    20,     4,    -1,     3,
      26,    35,    21,     4,    -1,     3,    26,    35,    22,     4,
      -1,     3,    26,    35,    23,     4,    -1,     3,    26,    35,
      24,     4,    -1,     3,    26,    35,    19,     5,    -1,     3,
      26,    35,    20,     5,    -1,     3,    26,    35,    21,     5,
      -1,     3,    26,    35,    22,     5,    -1,     3,    26,    35,
      23,     5,    -1,     3,    26,    35,    24,     5,    -1,     3,
      26,    35,    19,     6,    -1,     3,    26,    35,    20,     6,
      -1,     3,    26,    35,    21,     6,    -1,     3,    26,    35,
      22,     6,    -1,     3,    26,    35,    23,     6,    -1,     3,
      26,    35,    24,     6,    -1
};

/* YYRLINE[YYN] -- source line where rule number YYN was defined.  */
static const yytype_uint16 yyrline[] =
{
       0,   169,   169,   175,   196,   199,   205,   210,   214,   220,
     224,   235,   238,   244,   250,   253,   259,   263,   271,   275,
     280,   290,   293,   299,   306,   309,   315,   318,   325,   328,
     334,   341,   344,   347,   350,   353,   360,   364,   368,   372,
     376,   380,   384,   388,   392,   396,   400,   404,   408,   412,
     416,   420,   424,   428,   432,   436,   440,   444,   448,   452
};
#endif

#if YYDEBUG || YYERROR_VERBOSE || YYTOKEN_TABLE
/* YYTNAME[SYMBOL-NUM] -- String name of the symbol SYMBOL-NUM.
   First, the terminals, then, starting at YYNTOKENS, nonterminals.  */
static const char *const yytname[] =
{
  "$end", "error", "$undefined", "IDENTIFIER", "INT_LITERAL",
  "FLOAT_LITERAL", "STRING_LITERAL", "SELECT", "FROM", "WHERE", "JOIN",
  "ON", "AS", "AND", "OR", "NOT", "GROUP", "BY", "HAVING", "EQ", "LT",
  "GT", "LEQ", "GEQ", "NEQ", "','", "'.'", "'*'", "'('", "')'", "$accept",
  "start", "query_stmt", "column_list", "column", "dotted_identifier",
  "join_list", "join_table", "table_item", "subquery", "table_ref",
  "opt_where_clause", "where_clause", "opt_group_by", "group_by_cols",
  "opt_having_clause", "join_condition", "condition", "comparison_expr", 0
};
#endif

# ifdef YYPRINT
/* YYTOKNUM[YYLEX-NUM] -- Internal token number corresponding to
   token YYLEX-NUM.  */
static const yytype_uint16 yytoknum[] =
{
       0,   256,   257,   258,   259,   260,   261,   262,   263,   264,
     265,   266,   267,   268,   269,   270,   271,   272,   273,   274,
     275,   276,   277,   278,   279,    44,    46,    42,    40,    41
};
# endif

/* YYR1[YYN] -- Symbol number of symbol that rule YYN derives.  */
static const yytype_uint8 yyr1[] =
{
       0,    30,    31,    32,    33,    33,    34,    34,    34,    35,
      35,    36,    36,    37,    38,    38,    39,    39,    40,    40,
      40,    41,    41,    42,    43,    43,    44,    44,    45,    45,
      46,    47,    47,    47,    47,    47,    48,    48,    48,    48,
      48,    48,    48,    48,    48,    48,    48,    48,    48,    48,
      48,    48,    48,    48,    48,    48,    48,    48,    48,    48
};

/* YYR2[YYN] -- Number of symbols composing right hand side of rule YYN.  */
static const yytype_uint8 yyr2[] =
{
       0,     2,     1,     7,     1,     3,     3,     3,     1,     1,
       3,     1,     5,     1,     1,     1,     5,     4,     1,     3,
       2,     0,     1,     2,     0,     3,     1,     3,     0,     2,
       1,     1,     3,     3,     2,     3,     7,     7,     7,     7,
       7,     7,     5,     5,     5,     5,     5,     5,     5,     5,
       5,     5,     5,     5,     5,     5,     5,     5,     5,     5
};

/* YYDEFACT[STATE-NAME] -- Default rule to reduce with in state
   STATE-NUM when YYTABLE doesn't specify something else to do.  Zero
   means the default is an error.  */
static const yytype_uint8 yydefact[] =
{
       0,     0,     0,     2,     0,     8,     0,     4,     1,     0,
       0,     0,     9,     7,     6,    18,     0,    21,    11,    15,
      14,     5,     0,    20,     0,     0,     0,     0,    24,    22,
      10,    19,     0,     0,     0,     0,    23,    31,     0,    13,
       0,    28,    17,     0,     0,    34,     0,     0,     0,     0,
       0,     0,     3,    16,     0,    35,    32,    33,    12,    30,
      26,    25,    29,     0,     0,     0,     0,     0,     0,     0,
       0,    42,    48,    54,     0,    43,    49,    55,     0,    44,
      50,    56,     0,    45,    51,    57,     0,    46,    52,    58,
       0,    47,    53,    59,    27,     0,     0,     0,     0,     0,
       0,    36,    37,    38,    39,    40,    41
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int8 yydefgoto[] =
{
      -1,     2,     3,     6,     7,    14,    17,    38,    18,    19,
      20,    28,    29,    41,    61,    52,    58,    36,    37
};

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
#define YYPACT_NINF -44
static const yytype_int8 yypact[] =
{
      -3,     2,    15,   -44,   -13,   -44,     1,   -44,   -44,     3,
       0,     2,   -44,   -44,    12,     7,    -3,    22,   -44,   -44,
     -44,   -44,    20,   -44,    43,    46,    -1,     0,    61,   -44,
     -44,   -44,    13,    50,    -1,    -1,    -2,   -44,    67,   -44,
      62,    63,   -44,    77,    79,   -44,     4,    -1,    -1,    -1,
       2,    -1,   -44,   -44,    21,   -44,   -44,    70,   -44,    -2,
     -44,    59,    -2,    31,    45,    56,    60,    64,    68,     2,
      65,   -44,   -44,   -44,    66,   -44,   -44,   -44,    69,   -44,
     -44,   -44,    71,   -44,   -44,   -44,    72,   -44,   -44,   -44,
      73,   -44,   -44,   -44,   -44,    79,    79,    79,    79,    79,
      79,    12,    12,    12,    12,    12,    12
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int8 yypgoto[] =
{
     -44,   -44,    74,   -44,   -11,   -43,   -44,   -44,    58,   -44,
     -44,   -44,   -44,   -44,   -44,   -44,   -44,   -27,   -44
};

/* YYTABLE[YYPACT[STATE-NUM]].  What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule which
   number is the opposite.  If zero, do what YYDEFACT says.
   If YYTABLE_NINF, syntax error.  */
#define YYTABLE_NINF -1
static const yytype_uint8 yytable[] =
{
      21,    54,    33,    15,     1,     4,    12,    45,    46,    10,
      23,    47,    48,     9,    34,     8,    42,    47,    48,    24,
      56,    57,    59,    30,    62,    43,    11,    35,    16,     5,
      13,    26,    27,    55,    70,    71,    72,    73,    22,    60,
      63,    64,    65,    66,    67,    68,    31,    22,    74,    75,
      76,    77,   101,   102,   103,   104,   105,   106,    94,    78,
      79,    80,    81,    82,    83,    84,    85,    86,    87,    88,
      89,    90,    91,    92,    93,    32,    44,    40,    49,    50,
      53,    51,    12,    47,    69,    39,     0,     0,     0,     0,
      25,    95,    96,     0,     0,    97,     0,    98,    99,   100
};

static const yytype_int8 yycheck[] =
{
      11,    44,     3,     3,     7,     3,     3,    34,    35,     8,
       3,    13,    14,    26,    15,     0,     3,    13,    14,    12,
      47,    48,    49,     3,    51,    12,    25,    28,    28,    27,
      27,     9,    10,    29,     3,     4,     5,     6,    26,    50,
      19,    20,    21,    22,    23,    24,     3,    26,     3,     4,
       5,     6,    95,    96,    97,    98,    99,   100,    69,     3,
       4,     5,     6,     3,     4,     5,     6,     3,     4,     5,
       6,     3,     4,     5,     6,    29,    26,    16,    11,    17,
       3,    18,     3,    13,    25,    27,    -1,    -1,    -1,    -1,
      16,    26,    26,    -1,    -1,    26,    -1,    26,    26,    26
};

/* YYSTOS[STATE-NUM] -- The (internal number of the) accessing
   symbol of state STATE-NUM.  */
static const yytype_uint8 yystos[] =
{
       0,     7,    31,    32,     3,    27,    33,    34,     0,    26,
       8,    25,     3,    27,    35,     3,    28,    36,    38,    39,
      40,    34,    26,     3,    12,    32,     9,    10,    41,    42,
       3,     3,    29,     3,    15,    28,    47,    48,    37,    38,
      16,    43,     3,    12,    26,    47,    47,    13,    14,    11,
      17,    18,    45,     3,    35,    29,    47,    47,    46,    47,
      34,    44,    47,    19,    20,    21,    22,    23,    24,    25,
       3,     4,     5,     6,     3,     4,     5,     6,     3,     4,
       5,     6,     3,     4,     5,     6,     3,     4,     5,     6,
       3,     4,     5,     6,    34,    26,    26,    26,    26,    26,
      26,    35,    35,    35,    35,    35,    35
};

#define yyerrok		(yyerrstatus = 0)
#define yyclearin	(yychar = YYEMPTY)
#define YYEMPTY		(-2)
#define YYEOF		0

#define YYACCEPT	goto yyacceptlab
#define YYABORT		goto yyabortlab
#define YYERROR		goto yyerrorlab


/* Like YYERROR except do call yyerror.  This remains here temporarily
   to ease the transition to the new meaning of YYERROR, for GCC.
   Once GCC version 2 has supplanted version 1, this can go.  */

#define YYFAIL		goto yyerrlab

#define YYRECOVERING()  (!!yyerrstatus)

#define YYBACKUP(Token, Value)					\
do								\
  if (yychar == YYEMPTY && yylen == 1)				\
    {								\
      yychar = (Token);						\
      yylval = (Value);						\
      yytoken = YYTRANSLATE (yychar);				\
      YYPOPSTACK (1);						\
      goto yybackup;						\
    }								\
  else								\
    {								\
      yyerror (YY_("syntax error: cannot back up")); \
      YYERROR;							\
    }								\
while (YYID (0))


#define YYTERROR	1
#define YYERRCODE	256


/* YYLLOC_DEFAULT -- Set CURRENT to span from RHS[1] to RHS[N].
   If N is 0, then set CURRENT to the empty location which ends
   the previous symbol: RHS[0] (always defined).  */

#define YYRHSLOC(Rhs, K) ((Rhs)[K])
#ifndef YYLLOC_DEFAULT
# define YYLLOC_DEFAULT(Current, Rhs, N)				\
    do									\
      if (YYID (N))                                                    \
	{								\
	  (Current).first_line   = YYRHSLOC (Rhs, 1).first_line;	\
	  (Current).first_column = YYRHSLOC (Rhs, 1).first_column;	\
	  (Current).last_line    = YYRHSLOC (Rhs, N).last_line;		\
	  (Current).last_column  = YYRHSLOC (Rhs, N).last_column;	\
	}								\
      else								\
	{								\
	  (Current).first_line   = (Current).last_line   =		\
	    YYRHSLOC (Rhs, 0).last_line;				\
	  (Current).first_column = (Current).last_column =		\
	    YYRHSLOC (Rhs, 0).last_column;				\
	}								\
    while (YYID (0))
#endif


/* YY_LOCATION_PRINT -- Print the location on the stream.
   This macro was not mandated originally: define only if we know
   we won't break user code: when these are the locations we know.  */

#ifndef YY_LOCATION_PRINT
# if defined YYLTYPE_IS_TRIVIAL && YYLTYPE_IS_TRIVIAL
#  define YY_LOCATION_PRINT(File, Loc)			\
     fprintf (File, "%d.%d-%d.%d",			\
	      (Loc).first_line, (Loc).first_column,	\
	      (Loc).last_line,  (Loc).last_column)
# else
#  define YY_LOCATION_PRINT(File, Loc) ((void) 0)
# endif
#endif


/* YYLEX -- calling `yylex' with the right arguments.  */

#ifdef YYLEX_PARAM
# define YYLEX yylex (YYLEX_PARAM)
#else
# define YYLEX yylex ()
#endif

/* Enable debugging if requested.  */
#if YYDEBUG

# ifndef YYFPRINTF
#  include <stdio.h> /* INFRINGES ON USER NAME SPACE */
#  define YYFPRINTF fprintf
# endif

# define YYDPRINTF(Args)			\
do {						\
  if (yydebug)					\
    YYFPRINTF Args;				\
} while (YYID (0))

# define YY_SYMBOL_PRINT(Title, Type, Value, Location)			  \
do {									  \
  if (yydebug)								  \
    {									  \
      YYFPRINTF (stderr, "%s ", Title);					  \
      yy_symbol_print (stderr,						  \
		  Type, Value); \
      YYFPRINTF (stderr, "\n");						  \
    }									  \
} while (YYID (0))


/*--------------------------------.
| Print this symbol on YYOUTPUT.  |
`--------------------------------*/

/*ARGSUSED*/
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_symbol_value_print (FILE *yyoutput, int yytype, YYSTYPE const * const yyvaluep)
#else
static void
yy_symbol_value_print (yyoutput, yytype, yyvaluep)
    FILE *yyoutput;
    int yytype;
    YYSTYPE const * const yyvaluep;
#endif
{
  if (!yyvaluep)
    return;
# ifdef YYPRINT
  if (yytype < YYNTOKENS)
    YYPRINT (yyoutput, yytoknum[yytype], *yyvaluep);
# else
  YYUSE (yyoutput);
# endif
  switch (yytype)
    {
      default:
	break;
    }
}


/*--------------------------------.
| Print this symbol on YYOUTPUT.  |
`--------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_symbol_print (FILE *yyoutput, int yytype, YYSTYPE const * const yyvaluep)
#else
static void
yy_symbol_print (yyoutput, yytype, yyvaluep)
    FILE *yyoutput;
    int yytype;
    YYSTYPE const * const yyvaluep;
#endif
{
  if (yytype < YYNTOKENS)
    YYFPRINTF (yyoutput, "token %s (", yytname[yytype]);
  else
    YYFPRINTF (yyoutput, "nterm %s (", yytname[yytype]);

  yy_symbol_value_print (yyoutput, yytype, yyvaluep);
  YYFPRINTF (yyoutput, ")");
}

/*------------------------------------------------------------------.
| yy_stack_print -- Print the state stack from its BOTTOM up to its |
| TOP (included).                                                   |
`------------------------------------------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_stack_print (yytype_int16 *bottom, yytype_int16 *top)
#else
static void
yy_stack_print (bottom, top)
    yytype_int16 *bottom;
    yytype_int16 *top;
#endif
{
  YYFPRINTF (stderr, "Stack now");
  for (; bottom <= top; ++bottom)
    YYFPRINTF (stderr, " %d", *bottom);
  YYFPRINTF (stderr, "\n");
}

# define YY_STACK_PRINT(Bottom, Top)				\
do {								\
  if (yydebug)							\
    yy_stack_print ((Bottom), (Top));				\
} while (YYID (0))


/*------------------------------------------------.
| Report that the YYRULE is going to be reduced.  |
`------------------------------------------------*/

#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yy_reduce_print (YYSTYPE *yyvsp, int yyrule)
#else
static void
yy_reduce_print (yyvsp, yyrule)
    YYSTYPE *yyvsp;
    int yyrule;
#endif
{
  int yynrhs = yyr2[yyrule];
  int yyi;
  unsigned long int yylno = yyrline[yyrule];
  YYFPRINTF (stderr, "Reducing stack by rule %d (line %lu):\n",
	     yyrule - 1, yylno);
  /* The symbols being reduced.  */
  for (yyi = 0; yyi < yynrhs; yyi++)
    {
      fprintf (stderr, "   $%d = ", yyi + 1);
      yy_symbol_print (stderr, yyrhs[yyprhs[yyrule] + yyi],
		       &(yyvsp[(yyi + 1) - (yynrhs)])
		       		       );
      fprintf (stderr, "\n");
    }
}

# define YY_REDUCE_PRINT(Rule)		\
do {					\
  if (yydebug)				\
    yy_reduce_print (yyvsp, Rule); \
} while (YYID (0))

/* Nonzero means print parse trace.  It is left uninitialized so that
   multiple parsers can coexist.  */
int yydebug;
#else /* !YYDEBUG */
# define YYDPRINTF(Args)
# define YY_SYMBOL_PRINT(Title, Type, Value, Location)
# define YY_STACK_PRINT(Bottom, Top)
# define YY_REDUCE_PRINT(Rule)
#endif /* !YYDEBUG */


/* YYINITDEPTH -- initial size of the parser's stacks.  */
#ifndef	YYINITDEPTH
# define YYINITDEPTH 200
#endif

/* YYMAXDEPTH -- maximum size the stacks can grow to (effective only
   if the built-in stack extension method is used).

   Do not make this value too large; the results are undefined if
   YYSTACK_ALLOC_MAXIMUM < YYSTACK_BYTES (YYMAXDEPTH)
   evaluated with infinite-precision integer arithmetic.  */

#ifndef YYMAXDEPTH
# define YYMAXDEPTH 10000
#endif



#if YYERROR_VERBOSE

# ifndef yystrlen
#  if defined __GLIBC__ && defined _STRING_H
#   define yystrlen strlen
#  else
/* Return the length of YYSTR.  */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static YYSIZE_T
yystrlen (const char *yystr)
#else
static YYSIZE_T
yystrlen (yystr)
    const char *yystr;
#endif
{
  YYSIZE_T yylen;
  for (yylen = 0; yystr[yylen]; yylen++)
    continue;
  return yylen;
}
#  endif
# endif

# ifndef yystpcpy
#  if defined __GLIBC__ && defined _STRING_H && defined _GNU_SOURCE
#   define yystpcpy stpcpy
#  else
/* Copy YYSRC to YYDEST, returning the address of the terminating '\0' in
   YYDEST.  */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static char *
yystpcpy (char *yydest, const char *yysrc)
#else
static char *
yystpcpy (yydest, yysrc)
    char *yydest;
    const char *yysrc;
#endif
{
  char *yyd = yydest;
  const char *yys = yysrc;

  while ((*yyd++ = *yys++) != '\0')
    continue;

  return yyd - 1;
}
#  endif
# endif

# ifndef yytnamerr
/* Copy to YYRES the contents of YYSTR after stripping away unnecessary
   quotes and backslashes, so that it's suitable for yyerror.  The
   heuristic is that double-quoting is unnecessary unless the string
   contains an apostrophe, a comma, or backslash (other than
   backslash-backslash).  YYSTR is taken from yytname.  If YYRES is
   null, do not copy; instead, return the length of what the result
   would have been.  */
static YYSIZE_T
yytnamerr (char *yyres, const char *yystr)
{
  if (*yystr == '"')
    {
      YYSIZE_T yyn = 0;
      char const *yyp = yystr;

      for (;;)
	switch (*++yyp)
	  {
	  case '\'':
	  case ',':
	    goto do_not_strip_quotes;

	  case '\\':
	    if (*++yyp != '\\')
	      goto do_not_strip_quotes;
	    /* Fall through.  */
	  default:
	    if (yyres)
	      yyres[yyn] = *yyp;
	    yyn++;
	    break;

	  case '"':
	    if (yyres)
	      yyres[yyn] = '\0';
	    return yyn;
	  }
    do_not_strip_quotes: ;
    }

  if (! yyres)
    return yystrlen (yystr);

  return yystpcpy (yyres, yystr) - yyres;
}
# endif

/* Copy into YYRESULT an error message about the unexpected token
   YYCHAR while in state YYSTATE.  Return the number of bytes copied,
   including the terminating null byte.  If YYRESULT is null, do not
   copy anything; just return the number of bytes that would be
   copied.  As a special case, return 0 if an ordinary "syntax error"
   message will do.  Return YYSIZE_MAXIMUM if overflow occurs during
   size calculation.  */
static YYSIZE_T
yysyntax_error (char *yyresult, int yystate, int yychar)
{
  int yyn = yypact[yystate];

  if (! (YYPACT_NINF < yyn && yyn <= YYLAST))
    return 0;
  else
    {
      int yytype = YYTRANSLATE (yychar);
      YYSIZE_T yysize0 = yytnamerr (0, yytname[yytype]);
      YYSIZE_T yysize = yysize0;
      YYSIZE_T yysize1;
      int yysize_overflow = 0;
      enum { YYERROR_VERBOSE_ARGS_MAXIMUM = 5 };
      char const *yyarg[YYERROR_VERBOSE_ARGS_MAXIMUM];
      int yyx;

# if 0
      /* This is so xgettext sees the translatable formats that are
	 constructed on the fly.  */
      YY_("syntax error, unexpected %s");
      YY_("syntax error, unexpected %s, expecting %s");
      YY_("syntax error, unexpected %s, expecting %s or %s");
      YY_("syntax error, unexpected %s, expecting %s or %s or %s");
      YY_("syntax error, unexpected %s, expecting %s or %s or %s or %s");
# endif
      char *yyfmt;
      char const *yyf;
      static char const yyunexpected[] = "syntax error, unexpected %s";
      static char const yyexpecting[] = ", expecting %s";
      static char const yyor[] = " or %s";
      char yyformat[sizeof yyunexpected
		    + sizeof yyexpecting - 1
		    + ((YYERROR_VERBOSE_ARGS_MAXIMUM - 2)
		       * (sizeof yyor - 1))];
      char const *yyprefix = yyexpecting;

      /* Start YYX at -YYN if negative to avoid negative indexes in
	 YYCHECK.  */
      int yyxbegin = yyn < 0 ? -yyn : 0;

      /* Stay within bounds of both yycheck and yytname.  */
      int yychecklim = YYLAST - yyn + 1;
      int yyxend = yychecklim < YYNTOKENS ? yychecklim : YYNTOKENS;
      int yycount = 1;

      yyarg[0] = yytname[yytype];
      yyfmt = yystpcpy (yyformat, yyunexpected);

      for (yyx = yyxbegin; yyx < yyxend; ++yyx)
	if (yycheck[yyx + yyn] == yyx && yyx != YYTERROR)
	  {
	    if (yycount == YYERROR_VERBOSE_ARGS_MAXIMUM)
	      {
		yycount = 1;
		yysize = yysize0;
		yyformat[sizeof yyunexpected - 1] = '\0';
		break;
	      }
	    yyarg[yycount++] = yytname[yyx];
	    yysize1 = yysize + yytnamerr (0, yytname[yyx]);
	    yysize_overflow |= (yysize1 < yysize);
	    yysize = yysize1;
	    yyfmt = yystpcpy (yyfmt, yyprefix);
	    yyprefix = yyor;
	  }

      yyf = YY_(yyformat);
      yysize1 = yysize + yystrlen (yyf);
      yysize_overflow |= (yysize1 < yysize);
      yysize = yysize1;

      if (yysize_overflow)
	return YYSIZE_MAXIMUM;

      if (yyresult)
	{
	  /* Avoid sprintf, as that infringes on the user's name space.
	     Don't have undefined behavior even if the translation
	     produced a string with the wrong number of "%s"s.  */
	  char *yyp = yyresult;
	  int yyi = 0;
	  while ((*yyp = *yyf) != '\0')
	    {
	      if (*yyp == '%' && yyf[1] == 's' && yyi < yycount)
		{
		  yyp += yytnamerr (yyp, yyarg[yyi++]);
		  yyf += 2;
		}
	      else
		{
		  yyp++;
		  yyf++;
		}
	    }
	}
      return yysize;
    }
}
#endif /* YYERROR_VERBOSE */


/*-----------------------------------------------.
| Release the memory associated to this symbol.  |
`-----------------------------------------------*/

/*ARGSUSED*/
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
static void
yydestruct (const char *yymsg, int yytype, YYSTYPE *yyvaluep)
#else
static void
yydestruct (yymsg, yytype, yyvaluep)
    const char *yymsg;
    int yytype;
    YYSTYPE *yyvaluep;
#endif
{
  YYUSE (yyvaluep);

  if (!yymsg)
    yymsg = "Deleting";
  YY_SYMBOL_PRINT (yymsg, yytype, yyvaluep, yylocationp);

  switch (yytype)
    {

      default:
	break;
    }
}


/* Prevent warnings from -Wmissing-prototypes.  */

#ifdef YYPARSE_PARAM
#if defined __STDC__ || defined __cplusplus
int yyparse (void *YYPARSE_PARAM);
#else
int yyparse ();
#endif
#else /* ! YYPARSE_PARAM */
#if defined __STDC__ || defined __cplusplus
int yyparse (void);
#else
int yyparse ();
#endif
#endif /* ! YYPARSE_PARAM */



/* The look-ahead symbol.  */
int yychar;

/* The semantic value of the look-ahead symbol.  */
YYSTYPE yylval;

/* Number of syntax errors so far.  */
int yynerrs;



/*----------.
| yyparse.  |
`----------*/

#ifdef YYPARSE_PARAM
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
int
yyparse (void *YYPARSE_PARAM)
#else
int
yyparse (YYPARSE_PARAM)
    void *YYPARSE_PARAM;
#endif
#else /* ! YYPARSE_PARAM */
#if (defined __STDC__ || defined __C99__FUNC__ \
     || defined __cplusplus || defined _MSC_VER)
int
yyparse (void)
#else
int
yyparse ()

#endif
#endif
{
  
  int yystate;
  int yyn;
  int yyresult;
  /* Number of tokens to shift before error messages enabled.  */
  int yyerrstatus;
  /* Look-ahead token as an internal (translated) token number.  */
  int yytoken = 0;
#if YYERROR_VERBOSE
  /* Buffer for error messages, and its allocated size.  */
  char yymsgbuf[128];
  char *yymsg = yymsgbuf;
  YYSIZE_T yymsg_alloc = sizeof yymsgbuf;
#endif

  /* Three stacks and their tools:
     `yyss': related to states,
     `yyvs': related to semantic values,
     `yyls': related to locations.

     Refer to the stacks thru separate pointers, to allow yyoverflow
     to reallocate them elsewhere.  */

  /* The state stack.  */
  yytype_int16 yyssa[YYINITDEPTH];
  yytype_int16 *yyss = yyssa;
  yytype_int16 *yyssp;

  /* The semantic value stack.  */
  YYSTYPE yyvsa[YYINITDEPTH];
  YYSTYPE *yyvs = yyvsa;
  YYSTYPE *yyvsp;



#define YYPOPSTACK(N)   (yyvsp -= (N), yyssp -= (N))

  YYSIZE_T yystacksize = YYINITDEPTH;

  /* The variables used to return semantic value and location from the
     action routines.  */
  YYSTYPE yyval;


  /* The number of symbols on the RHS of the reduced rule.
     Keep to zero when no symbol should be popped.  */
  int yylen = 0;

  YYDPRINTF ((stderr, "Starting parse\n"));

  yystate = 0;
  yyerrstatus = 0;
  yynerrs = 0;
  yychar = YYEMPTY;		/* Cause a token to be read.  */

  /* Initialize stack pointers.
     Waste one element of value and location stack
     so that they stay on the same level as the state stack.
     The wasted elements are never initialized.  */

  yyssp = yyss;
  yyvsp = yyvs;

  goto yysetstate;

/*------------------------------------------------------------.
| yynewstate -- Push a new state, which is found in yystate.  |
`------------------------------------------------------------*/
 yynewstate:
  /* In all cases, when you get here, the value and location stacks
     have just been pushed.  So pushing a state here evens the stacks.  */
  yyssp++;

 yysetstate:
  *yyssp = yystate;

  if (yyss + yystacksize - 1 <= yyssp)
    {
      /* Get the current used size of the three stacks, in elements.  */
      YYSIZE_T yysize = yyssp - yyss + 1;

#ifdef yyoverflow
      {
	/* Give user a chance to reallocate the stack.  Use copies of
	   these so that the &'s don't force the real ones into
	   memory.  */
	YYSTYPE *yyvs1 = yyvs;
	yytype_int16 *yyss1 = yyss;


	/* Each stack pointer address is followed by the size of the
	   data in use in that stack, in bytes.  This used to be a
	   conditional around just the two extra args, but that might
	   be undefined if yyoverflow is a macro.  */
	yyoverflow (YY_("memory exhausted"),
		    &yyss1, yysize * sizeof (*yyssp),
		    &yyvs1, yysize * sizeof (*yyvsp),

		    &yystacksize);

	yyss = yyss1;
	yyvs = yyvs1;
      }
#else /* no yyoverflow */
# ifndef YYSTACK_RELOCATE
      goto yyexhaustedlab;
# else
      /* Extend the stack our own way.  */
      if (YYMAXDEPTH <= yystacksize)
	goto yyexhaustedlab;
      yystacksize *= 2;
      if (YYMAXDEPTH < yystacksize)
	yystacksize = YYMAXDEPTH;

      {
	yytype_int16 *yyss1 = yyss;
	union yyalloc *yyptr =
	  (union yyalloc *) YYSTACK_ALLOC (YYSTACK_BYTES (yystacksize));
	if (! yyptr)
	  goto yyexhaustedlab;
	YYSTACK_RELOCATE (yyss);
	YYSTACK_RELOCATE (yyvs);

#  undef YYSTACK_RELOCATE
	if (yyss1 != yyssa)
	  YYSTACK_FREE (yyss1);
      }
# endif
#endif /* no yyoverflow */

      yyssp = yyss + yysize - 1;
      yyvsp = yyvs + yysize - 1;


      YYDPRINTF ((stderr, "Stack size increased to %lu\n",
		  (unsigned long int) yystacksize));

      if (yyss + yystacksize - 1 <= yyssp)
	YYABORT;
    }

  YYDPRINTF ((stderr, "Entering state %d\n", yystate));

  goto yybackup;

/*-----------.
| yybackup.  |
`-----------*/
yybackup:

  /* Do appropriate processing given the current state.  Read a
     look-ahead token if we need one and don't already have one.  */

  /* First try to decide what to do without reference to look-ahead token.  */
  yyn = yypact[yystate];
  if (yyn == YYPACT_NINF)
    goto yydefault;

  /* Not known => get a look-ahead token if don't already have one.  */

  /* YYCHAR is either YYEMPTY or YYEOF or a valid look-ahead symbol.  */
  if (yychar == YYEMPTY)
    {
      YYDPRINTF ((stderr, "Reading a token: "));
      yychar = YYLEX;
    }

  if (yychar <= YYEOF)
    {
      yychar = yytoken = YYEOF;
      YYDPRINTF ((stderr, "Now at end of input.\n"));
    }
  else
    {
      yytoken = YYTRANSLATE (yychar);
      YY_SYMBOL_PRINT ("Next token is", yytoken, &yylval, &yylloc);
    }

  /* If the proper action on seeing token YYTOKEN is to reduce or to
     detect an error, take that action.  */
  yyn += yytoken;
  if (yyn < 0 || YYLAST < yyn || yycheck[yyn] != yytoken)
    goto yydefault;
  yyn = yytable[yyn];
  if (yyn <= 0)
    {
      if (yyn == 0 || yyn == YYTABLE_NINF)
	goto yyerrlab;
      yyn = -yyn;
      goto yyreduce;
    }

  if (yyn == YYFINAL)
    YYACCEPT;

  /* Count tokens shifted since error; after three, turn off error
     status.  */
  if (yyerrstatus)
    yyerrstatus--;

  /* Shift the look-ahead token.  */
  YY_SYMBOL_PRINT ("Shifting", yytoken, &yylval, &yylloc);

  /* Discard the shifted token unless it is eof.  */
  if (yychar != YYEOF)
    yychar = YYEMPTY;

  yystate = yyn;
  *++yyvsp = yylval;

  goto yynewstate;


/*-----------------------------------------------------------.
| yydefault -- do the default action for the current state.  |
`-----------------------------------------------------------*/
yydefault:
  yyn = yydefact[yystate];
  if (yyn == 0)
    goto yyerrlab;
  goto yyreduce;


/*-----------------------------.
| yyreduce -- Do a reduction.  |
`-----------------------------*/
yyreduce:
  /* yyn is the number of a rule to reduce with.  */
  yylen = yyr2[yyn];

  /* If YYLEN is nonzero, implement the default value of the action:
     `$$ = $1'.

     Otherwise, the following line sets YYVAL to garbage.
     This behavior is undocumented and Bison
     users should not rely upon it.  Assigning to YYVAL
     unconditionally makes the parser a bit smaller, and it avoids a
     GCC warning that YYVAL may be used uninitialized.  */
  yyval = yyvsp[1-yylen];


  YY_REDUCE_PRINT (yyn);
  switch (yyn)
    {
        case 2:
#line 169 "sql_parser.y"
    {
        result = (yyvsp[(1) - (1)].node);
    ;}
    break;

  case 3:
#line 175 "sql_parser.y"
    {
        //Step 6a: Build the base project node over the join list
        RelNode *base = (yyvsp[(4) - (7)].node);

        //Step 6b: Apply WHERE selection if present
        if ((yyvsp[(5) - (7)].cond) != NULL) {
            base = create_select_node(base, (yyvsp[(5) - (7)].cond));
        }

        //Step 6c: Apply GROUP BY with optional HAVING if present
        if ((yyvsp[(6) - (7)].col) != NULL) {
            base = create_groupby_node(base, (yyvsp[(6) - (7)].col), (yyvsp[(7) - (7)].cond));
        }

        //Step 6d: Apply projection of column list
        (yyval.node) = create_project_node(base, (yyvsp[(2) - (7)].col));
    ;}
    break;

  case 4:
#line 196 "sql_parser.y"
    {
        (yyval.col) = (yyvsp[(1) - (1)].col);
    ;}
    break;

  case 5:
#line 199 "sql_parser.y"
    {
        (yyval.col) = append_column((yyvsp[(1) - (3)].col), (yyvsp[(3) - (3)].col));
    ;}
    break;

  case 6:
#line 205 "sql_parser.y"
    {
        (yyval.col) = create_column((yyvsp[(1) - (3)].strval), (yyvsp[(3) - (3)].strval));
        free((yyvsp[(1) - (3)].strval));
        free((yyvsp[(3) - (3)].strval));
    ;}
    break;

  case 7:
#line 210 "sql_parser.y"
    {
        (yyval.col) = create_column((yyvsp[(1) - (3)].strval), strdup("*"));
        free((yyvsp[(1) - (3)].strval));
    ;}
    break;

  case 8:
#line 214 "sql_parser.y"
    {
        (yyval.col) = create_column(strdup("*"), strdup("*"));
    ;}
    break;

  case 9:
#line 220 "sql_parser.y"
    {
        (yyval.strval) = strdup((yyvsp[(1) - (1)].strval));
        free((yyvsp[(1) - (1)].strval));
    ;}
    break;

  case 10:
#line 224 "sql_parser.y"
    {
        char *temp = (char *)malloc(strlen((yyvsp[(1) - (3)].strval)) + strlen((yyvsp[(3) - (3)].strval)) + 2);
        sprintf(temp, "%s.%s", (yyvsp[(1) - (3)].strval), (yyvsp[(3) - (3)].strval));
        (yyval.strval) = temp;
        free((yyvsp[(1) - (3)].strval));
        free((yyvsp[(3) - (3)].strval));
    ;}
    break;

  case 11:
#line 235 "sql_parser.y"
    {
        (yyval.node) = (yyvsp[(1) - (1)].node);
    ;}
    break;

  case 12:
#line 238 "sql_parser.y"
    {
        (yyval.node) = create_join_node((yyvsp[(1) - (5)].node), (yyvsp[(3) - (5)].node), (yyvsp[(5) - (5)].cond));
    ;}
    break;

  case 13:
#line 244 "sql_parser.y"
    {
        (yyval.node) = (yyvsp[(1) - (1)].node);
    ;}
    break;

  case 14:
#line 250 "sql_parser.y"
    {
        (yyval.node) = create_base_relation((yyvsp[(1) - (1)].tbl));
    ;}
    break;

  case 15:
#line 253 "sql_parser.y"
    {
        (yyval.node) = (yyvsp[(1) - (1)].node);
    ;}
    break;

  case 16:
#line 259 "sql_parser.y"
    {
        (yyval.node) = create_subquery_node((yyvsp[(2) - (5)].node), (yyvsp[(5) - (5)].strval));
        free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 17:
#line 263 "sql_parser.y"
    {
        //Step 8a: Implicit AS for subquery alias
        (yyval.node) = create_subquery_node((yyvsp[(2) - (4)].node), (yyvsp[(4) - (4)].strval));
        free((yyvsp[(4) - (4)].strval));
    ;}
    break;

  case 18:
#line 271 "sql_parser.y"
    {
        (yyval.tbl) = create_table((yyvsp[(1) - (1)].strval), NULL);
        free((yyvsp[(1) - (1)].strval));
    ;}
    break;

  case 19:
#line 275 "sql_parser.y"
    {
        (yyval.tbl) = create_table((yyvsp[(1) - (3)].strval), (yyvsp[(3) - (3)].strval));
        free((yyvsp[(1) - (3)].strval));
        free((yyvsp[(3) - (3)].strval));
    ;}
    break;

  case 20:
#line 280 "sql_parser.y"
    {
        //Step 8b: Implicit AS for table alias
        (yyval.tbl) = create_table((yyvsp[(1) - (2)].strval), (yyvsp[(2) - (2)].strval));
        free((yyvsp[(1) - (2)].strval));
        free((yyvsp[(2) - (2)].strval));
    ;}
    break;

  case 21:
#line 290 "sql_parser.y"
    {
        (yyval.cond) = NULL;
    ;}
    break;

  case 22:
#line 293 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(1) - (1)].cond);
    ;}
    break;

  case 23:
#line 299 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(2) - (2)].cond);
    ;}
    break;

  case 24:
#line 306 "sql_parser.y"
    {
        (yyval.col) = NULL;
    ;}
    break;

  case 25:
#line 309 "sql_parser.y"
    {
        (yyval.col) = (yyvsp[(3) - (3)].col);
    ;}
    break;

  case 26:
#line 315 "sql_parser.y"
    {
        (yyval.col) = (yyvsp[(1) - (1)].col);
    ;}
    break;

  case 27:
#line 318 "sql_parser.y"
    {
        (yyval.col) = append_column((yyvsp[(1) - (3)].col), (yyvsp[(3) - (3)].col));
    ;}
    break;

  case 28:
#line 325 "sql_parser.y"
    {
        (yyval.cond) = NULL;
    ;}
    break;

  case 29:
#line 328 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(2) - (2)].cond);
    ;}
    break;

  case 30:
#line 334 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(1) - (1)].cond);
    ;}
    break;

  case 31:
#line 341 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(1) - (1)].cond);
    ;}
    break;

  case 32:
#line 344 "sql_parser.y"
    {
        (yyval.cond) = create_binary_condition(COND_AND, (yyvsp[(1) - (3)].cond), (yyvsp[(3) - (3)].cond));
    ;}
    break;

  case 33:
#line 347 "sql_parser.y"
    {
        (yyval.cond) = create_binary_condition(COND_OR, (yyvsp[(1) - (3)].cond), (yyvsp[(3) - (3)].cond));
    ;}
    break;

  case 34:
#line 350 "sql_parser.y"
    {
        (yyval.cond) = create_unary_condition(COND_NOT, (yyvsp[(2) - (2)].cond));
    ;}
    break;

  case 35:
#line 353 "sql_parser.y"
    {
        (yyval.cond) = (yyvsp[(2) - (3)].cond);
    ;}
    break;

  case 36:
#line 360 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_EQ, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 37:
#line 364 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LT, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 38:
#line 368 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GT, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 39:
#line 372 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LE, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 40:
#line 376 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GE, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 41:
#line 380 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_NE, (yyvsp[(1) - (7)].strval), (yyvsp[(3) - (7)].strval), 3, 0, 0.0, NULL, (yyvsp[(5) - (7)].strval), (yyvsp[(7) - (7)].strval));
        free((yyvsp[(1) - (7)].strval)); free((yyvsp[(3) - (7)].strval)); free((yyvsp[(5) - (7)].strval)); free((yyvsp[(7) - (7)].strval));
    ;}
    break;

  case 42:
#line 384 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_EQ, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 43:
#line 388 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 44:
#line 392 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 45:
#line 396 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 46:
#line 400 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 47:
#line 404 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_NE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 0, (yyvsp[(5) - (5)].intval), 0.0, NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 48:
#line 408 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_EQ, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 49:
#line 412 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 50:
#line 416 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 51:
#line 420 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 52:
#line 424 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 53:
#line 428 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_NE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 1, 0, (yyvsp[(5) - (5)].floatval), NULL, NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval));
    ;}
    break;

  case 54:
#line 432 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_EQ, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 55:
#line 436 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 56:
#line 440 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GT, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 57:
#line 444 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_LE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 58:
#line 448 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_GE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;

  case 59:
#line 452 "sql_parser.y"
    {
        (yyval.cond) = create_comparison(COND_NE, (yyvsp[(1) - (5)].strval), (yyvsp[(3) - (5)].strval), 2, 0, 0.0, (yyvsp[(5) - (5)].strval), NULL, NULL);
        free((yyvsp[(1) - (5)].strval)); free((yyvsp[(3) - (5)].strval)); free((yyvsp[(5) - (5)].strval));
    ;}
    break;


/* Line 1267 of yacc.c.  */
#line 2043 "y.tab.c"
      default: break;
    }
  YY_SYMBOL_PRINT ("-> $$ =", yyr1[yyn], &yyval, &yyloc);

  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);

  *++yyvsp = yyval;


  /* Now `shift' the result of the reduction.  Determine what state
     that goes to, based on the state we popped back to and the rule
     number reduced by.  */

  yyn = yyr1[yyn];

  yystate = yypgoto[yyn - YYNTOKENS] + *yyssp;
  if (0 <= yystate && yystate <= YYLAST && yycheck[yystate] == *yyssp)
    yystate = yytable[yystate];
  else
    yystate = yydefgoto[yyn - YYNTOKENS];

  goto yynewstate;


/*------------------------------------.
| yyerrlab -- here on detecting error |
`------------------------------------*/
yyerrlab:
  /* If not already recovering from an error, report this error.  */
  if (!yyerrstatus)
    {
      ++yynerrs;
#if ! YYERROR_VERBOSE
      yyerror (YY_("syntax error"));
#else
      {
	YYSIZE_T yysize = yysyntax_error (0, yystate, yychar);
	if (yymsg_alloc < yysize && yymsg_alloc < YYSTACK_ALLOC_MAXIMUM)
	  {
	    YYSIZE_T yyalloc = 2 * yysize;
	    if (! (yysize <= yyalloc && yyalloc <= YYSTACK_ALLOC_MAXIMUM))
	      yyalloc = YYSTACK_ALLOC_MAXIMUM;
	    if (yymsg != yymsgbuf)
	      YYSTACK_FREE (yymsg);
	    yymsg = (char *) YYSTACK_ALLOC (yyalloc);
	    if (yymsg)
	      yymsg_alloc = yyalloc;
	    else
	      {
		yymsg = yymsgbuf;
		yymsg_alloc = sizeof yymsgbuf;
	      }
	  }

	if (0 < yysize && yysize <= yymsg_alloc)
	  {
	    (void) yysyntax_error (yymsg, yystate, yychar);
	    yyerror (yymsg);
	  }
	else
	  {
	    yyerror (YY_("syntax error"));
	    if (yysize != 0)
	      goto yyexhaustedlab;
	  }
      }
#endif
    }



  if (yyerrstatus == 3)
    {
      /* If just tried and failed to reuse look-ahead token after an
	 error, discard it.  */

      if (yychar <= YYEOF)
	{
	  /* Return failure if at end of input.  */
	  if (yychar == YYEOF)
	    YYABORT;
	}
      else
	{
	  yydestruct ("Error: discarding",
		      yytoken, &yylval);
	  yychar = YYEMPTY;
	}
    }

  /* Else will try to reuse look-ahead token after shifting the error
     token.  */
  goto yyerrlab1;


/*---------------------------------------------------.
| yyerrorlab -- error raised explicitly by YYERROR.  |
`---------------------------------------------------*/
yyerrorlab:

  /* Pacify compilers like GCC when the user code never invokes
     YYERROR and the label yyerrorlab therefore never appears in user
     code.  */
  if (/*CONSTCOND*/ 0)
     goto yyerrorlab;

  /* Do not reclaim the symbols of the rule which action triggered
     this YYERROR.  */
  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);
  yystate = *yyssp;
  goto yyerrlab1;


/*-------------------------------------------------------------.
| yyerrlab1 -- common code for both syntax error and YYERROR.  |
`-------------------------------------------------------------*/
yyerrlab1:
  yyerrstatus = 3;	/* Each real token shifted decrements this.  */

  for (;;)
    {
      yyn = yypact[yystate];
      if (yyn != YYPACT_NINF)
	{
	  yyn += YYTERROR;
	  if (0 <= yyn && yyn <= YYLAST && yycheck[yyn] == YYTERROR)
	    {
	      yyn = yytable[yyn];
	      if (0 < yyn)
		break;
	    }
	}

      /* Pop the current state because it cannot handle the error token.  */
      if (yyssp == yyss)
	YYABORT;


      yydestruct ("Error: popping",
		  yystos[yystate], yyvsp);
      YYPOPSTACK (1);
      yystate = *yyssp;
      YY_STACK_PRINT (yyss, yyssp);
    }

  if (yyn == YYFINAL)
    YYACCEPT;

  *++yyvsp = yylval;


  /* Shift the error token.  */
  YY_SYMBOL_PRINT ("Shifting", yystos[yyn], yyvsp, yylsp);

  yystate = yyn;
  goto yynewstate;


/*-------------------------------------.
| yyacceptlab -- YYACCEPT comes here.  |
`-------------------------------------*/
yyacceptlab:
  yyresult = 0;
  goto yyreturn;

/*-----------------------------------.
| yyabortlab -- YYABORT comes here.  |
`-----------------------------------*/
yyabortlab:
  yyresult = 1;
  goto yyreturn;

#ifndef yyoverflow
/*-------------------------------------------------.
| yyexhaustedlab -- memory exhaustion comes here.  |
`-------------------------------------------------*/
yyexhaustedlab:
  yyerror (YY_("memory exhausted"));
  yyresult = 2;
  /* Fall through.  */
#endif

yyreturn:
  if (yychar != YYEOF && yychar != YYEMPTY)
     yydestruct ("Cleanup: discarding lookahead",
		 yytoken, &yylval);
  /* Do not reclaim the symbols of the rule which action triggered
     this YYABORT or YYACCEPT.  */
  YYPOPSTACK (yylen);
  YY_STACK_PRINT (yyss, yyssp);
  while (yyssp != yyss)
    {
      yydestruct ("Cleanup: popping",
		  yystos[*yyssp], yyvsp);
      YYPOPSTACK (1);
    }
#ifndef yyoverflow
  if (yyss != yyssa)
    YYSTACK_FREE (yyss);
#endif
#if YYERROR_VERBOSE
  if (yymsg != yymsgbuf)
    YYSTACK_FREE (yymsg);
#endif
  /* Make sure YYID is used.  */
  return YYID (yyresult);
}


#line 458 "sql_parser.y"


//Step 14: Error handler
void yyerror(const char *s) {
    fprintf(stderr, "Error: %s\n", s);
}

//Step 15: Helper function implementations

Column *create_column(char *table, char *attr) {
    Column *col = (Column *)malloc(sizeof(Column));
    col->table = strdup(table);
    col->attr = strdup(attr);
    col->next = NULL;
    return col;
}

Column *append_column(Column *list, Column *new_col) {
    if (list == NULL) return new_col;
    Column *cur = list;
    while (cur->next != NULL) cur = cur->next;
    cur->next = new_col;
    return list;
}

Table *create_table(char *name, char *alias) {
    Table *tbl = (Table *)malloc(sizeof(Table));
    tbl->name = strdup(name);
    tbl->alias = (alias != NULL) ? strdup(alias) : NULL;
    tbl->next = NULL;
    return tbl;
}

Table *append_table(Table *list, Table *new_table) {
    if (list == NULL) return new_table;
    Table *cur = list;
    while (cur->next != NULL) cur = cur->next;
    cur->next = new_table;
    return list;
}

Condition *create_comparison(CondType type, char *table, char *attr,
                             int literal_type, int int_val, float float_val,
                             char *str_val, char *cmp_table, char *cmp_attr) {
    Condition *cond = (Condition *)malloc(sizeof(Condition));
    cond->type = type;
    cond->expr.comparison.table = strdup(table);
    cond->expr.comparison.attr = strdup(attr);
    cond->expr.comparison.literal_type = literal_type;
    cond->expr.comparison.int_literal = 0;
    cond->expr.comparison.float_literal = 0.0;
    cond->expr.comparison.str_literal = NULL;
    cond->expr.comparison.cmp_table = NULL;
    cond->expr.comparison.cmp_attr = NULL;
    if (literal_type == 0) {
        cond->expr.comparison.int_literal = int_val;
    } else if (literal_type == 1) {
        cond->expr.comparison.float_literal = float_val;
    } else if (literal_type == 2) {
        cond->expr.comparison.str_literal = strdup(str_val);
    } else if (literal_type == 3) {
        cond->expr.comparison.cmp_table = strdup(cmp_table);
        cond->expr.comparison.cmp_attr = strdup(cmp_attr);
    }
    return cond;
}

Condition *create_binary_condition(CondType type, Condition *left, Condition *right) {
    Condition *cond = (Condition *)malloc(sizeof(Condition));
    cond->type = type;
    cond->expr.binary.left = left;
    cond->expr.binary.right = right;
    return cond;
}

Condition *create_unary_condition(CondType type, Condition *cond_expr) {
    Condition *cond = (Condition *)malloc(sizeof(Condition));
    cond->type = type;
    cond->expr.unary.cond = cond_expr;
    return cond;
}

RelNode *create_project_node(RelNode *input, Column *columns) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_PROJECT;
    node->op.project.input = input;
    node->op.project.columns = columns;
    node->tables = NULL;
    return node;
}

RelNode *create_select_node(RelNode *input, Condition *condition) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_SELECT;
    node->op.select.input = input;
    node->op.select.condition = condition;
    node->tables = NULL;
    return node;
}

RelNode *create_join_node(RelNode *left, RelNode *right, Condition *condition) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_JOIN;
    node->op.join.left = left;
    node->op.join.right = right;
    node->op.join.condition = condition;
    node->tables = NULL;
    return node;
}

RelNode *create_rename_node(RelNode *input, char *old_name, char *new_name) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_RENAME;
    node->op.rename.input = input;
    node->op.rename.old_name = strdup(old_name);
    node->op.rename.new_name = strdup(new_name);
    node->tables = NULL;
    return node;
}

RelNode *create_groupby_node(RelNode *input, Column *group_cols, Condition *having_cond) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_GROUPBY;
    node->op.groupby.input = input;
    node->op.groupby.group_cols = group_cols;
    node->op.groupby.having_cond = having_cond;
    node->tables = NULL;
    return node;
}

RelNode *create_base_relation(Table *tables) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = (RelOpType)-1; // mark as base relation
    node->tables = tables;
    return node;
}

RelNode *create_subquery_node(RelNode *subquery, char *alias) {
    RelNode *node = (RelNode *)malloc(sizeof(RelNode));
    node->op_type = OP_SUBQUERY;
    node->op.subquery.subquery = subquery;
    node->op.subquery.alias = strdup(alias);
    node->tables = NULL;
    return node;
}

//Step 16: JSON print helpers

static void print_indent(int indent) {
    int i;
    for (i = 0; i < indent; i++) printf(" ");
}

static void print_column_json(Column *col, int indent) {
    printf("[\n");
    while (col != NULL) {
        print_indent(indent + 2);
        printf("{\"table\": \"%s\", \"attr\": \"%s\"}", col->table, col->attr);
        col = col->next;
        if (col != NULL) printf(",");
        printf("\n");
    }
    print_indent(indent);
    printf("]");
}

static void print_table_json(Table *tbl, int indent) {
    printf("[\n");
    while (tbl != NULL) {
        print_indent(indent + 2);
        printf("{\"name\": \"%s\"", tbl->name);
        if (tbl->alias != NULL) printf(", \"alias\": \"%s\"", tbl->alias);
        printf("}");
        tbl = tbl->next;
        if (tbl != NULL) printf(",");
        printf("\n");
    }
    print_indent(indent);
    printf("]");
}

static void print_condition_json(Condition *cond, int indent) {
    if (cond == NULL) { printf("null"); return; }
    printf("{\n");
    print_indent(indent + 2);
    printf("\"type\": ");
    switch (cond->type) {
        case COND_EQ: printf("\"EQ\""); break;
        case COND_LT: printf("\"LT\""); break;
        case COND_GT: printf("\"GT\""); break;
        case COND_LE: printf("\"LE\""); break;
        case COND_GE: printf("\"GE\""); break;
        case COND_NE: printf("\"NE\""); break;
        case COND_AND:
            printf("\"AND\",\n");
            print_indent(indent + 2);
            printf("\"left\": ");
            print_condition_json(cond->expr.binary.left, indent + 2);
            printf(",\n");
            print_indent(indent + 2);
            printf("\"right\": ");
            print_condition_json(cond->expr.binary.right, indent + 2);
            break;
        case COND_OR:
            printf("\"OR\",\n");
            print_indent(indent + 2);
            printf("\"left\": ");
            print_condition_json(cond->expr.binary.left, indent + 2);
            printf(",\n");
            print_indent(indent + 2);
            printf("\"right\": ");
            print_condition_json(cond->expr.binary.right, indent + 2);
            break;
        case COND_NOT:
            printf("\"NOT\",\n");
            print_indent(indent + 2);
            printf("\"cond\": ");
            print_condition_json(cond->expr.unary.cond, indent + 2);
            break;
    }
    if (cond->type <= COND_NE) {
        printf(",\n");
        print_indent(indent + 2);
        printf("\"left\": {\"table\": \"%s\", \"attr\": \"%s\"},\n",
               cond->expr.comparison.table, cond->expr.comparison.attr);
        print_indent(indent + 2);
        printf("\"right\": ");
        if (cond->expr.comparison.literal_type == 0) {
            printf("{\"type\": \"int\", \"value\": %d}", cond->expr.comparison.int_literal);
        } else if (cond->expr.comparison.literal_type == 1) {
            printf("{\"type\": \"float\", \"value\": %f}", cond->expr.comparison.float_literal);
        } else if (cond->expr.comparison.literal_type == 2) {
            printf("{\"type\": \"string\", \"value\": \"%s\"}", cond->expr.comparison.str_literal);
        } else if (cond->expr.comparison.literal_type == 3) {
            printf("{\"type\": \"column\", \"table\": \"%s\", \"attr\": \"%s\"}",
                   cond->expr.comparison.cmp_table, cond->expr.comparison.cmp_attr);
        }
    }
    printf("\n");
    print_indent(indent);
    printf("}");
}

static void print_ra_tree_json_rec(RelNode *node, int indent) {
    if (node == NULL) { printf("null"); return; }
    printf("{\n");
    if (node->tables != NULL) {
        print_indent(indent + 2);
        printf("\"type\": \"base_relation\",\n");
        print_indent(indent + 2);
        printf("\"tables\": ");
        print_table_json(node->tables, indent + 2);
    } else {
        switch (node->op_type) {
            case OP_PROJECT:
                print_indent(indent + 2);
                printf("\"type\": \"project\",\n");
                print_indent(indent + 2);
                printf("\"columns\": ");
                print_column_json(node->op.project.columns, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"input\": ");
                print_ra_tree_json_rec(node->op.project.input, indent + 2);
                break;
            case OP_SELECT:
                print_indent(indent + 2);
                printf("\"type\": \"select\",\n");
                print_indent(indent + 2);
                printf("\"condition\": ");
                print_condition_json(node->op.select.condition, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"input\": ");
                print_ra_tree_json_rec(node->op.select.input, indent + 2);
                break;
            case OP_JOIN:
                print_indent(indent + 2);
                printf("\"type\": \"join\",\n");
                print_indent(indent + 2);
                printf("\"condition\": ");
                print_condition_json(node->op.join.condition, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"left\": ");
                print_ra_tree_json_rec(node->op.join.left, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"right\": ");
                print_ra_tree_json_rec(node->op.join.right, indent + 2);
                break;
            case OP_RENAME:
                print_indent(indent + 2);
                printf("\"type\": \"rename\",\n");
                print_indent(indent + 2);
                printf("\"old_name\": \"%s\",\n", node->op.rename.old_name);
                print_indent(indent + 2);
                printf("\"new_name\": \"%s\",\n", node->op.rename.new_name);
                print_indent(indent + 2);
                  printf("\"input\": ");
                print_ra_tree_json_rec(node->op.rename.input, indent + 2);
                break;
            case OP_GROUPBY:
                print_indent(indent + 2);
                printf("\"type\": \"groupby\",\n");
                print_indent(indent + 2);
                printf("\"group_cols\": ");
                print_column_json(node->op.groupby.group_cols, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"having\": ");
                print_condition_json(node->op.groupby.having_cond, indent + 2);
                printf(",\n");
                print_indent(indent + 2);
                printf("\"input\": ");
                print_ra_tree_json_rec(node->op.groupby.input, indent + 2);
                break;
            case OP_SUBQUERY:
                print_indent(indent + 2);
                printf("\"type\": \"subquery\",\n");
                print_indent(indent + 2);
                printf("\"alias\": \"%s\",\n", node->op.subquery.alias);
                print_indent(indent + 2);
                printf("\"query\": ");
                print_ra_tree_json_rec(node->op.subquery.subquery, indent + 2);
                break;
            default:
                print_indent(indent + 2);
                printf("\"type\": \"unknown\"");
                break;
        }
    }
    printf("\n");
    print_indent(indent);
    printf("}");
}

void print_ra_tree_json(RelNode *root) {
    print_ra_tree_json_rec(root, 0);
    printf("\n");
}

//Step 17: Memory free functions

void free_columns(Column *cols) {
    while (cols != NULL) {
        Column *next = cols->next;
        free(cols->table);
        free(cols->attr);
        free(cols);
        cols = next;
    }
}

void free_tables(Table *tables) {
    while (tables != NULL) {
        Table *next = tables->next;
        free(tables->name);
        if (tables->alias != NULL) free(tables->alias);
        free(tables);
        tables = next;
    }
}

void free_condition(Condition *cond) {
    if (cond == NULL) return;
    switch (cond->type) {
        case COND_AND:
        case COND_OR:
            free_condition(cond->expr.binary.left);
            free_condition(cond->expr.binary.right);
            break;
        case COND_NOT:
            free_condition(cond->expr.unary.cond);
            break;
        default:
            free(cond->expr.comparison.table);
            free(cond->expr.comparison.attr);
            if (cond->expr.comparison.literal_type == 2)
                free(cond->expr.comparison.str_literal);
            else if (cond->expr.comparison.literal_type == 3) {
                free(cond->expr.comparison.cmp_table);
                free(cond->expr.comparison.cmp_attr);
            }
            break;
    }
    free(cond);
}

void free_relnode(RelNode *node) {
    if (node == NULL) return;
    if (node->tables != NULL) {
        free_tables(node->tables);
    } else {
        switch (node->op_type) {
            case OP_PROJECT:
                free_columns(node->op.project.columns);
                free_relnode(node->op.project.input);
                break;
            case OP_SELECT:
                free_condition(node->op.select.condition);
                free_relnode(node->op.select.input);
                break;
            case OP_JOIN:
                free_condition(node->op.join.condition);
                free_relnode(node->op.join.left);
                free_relnode(node->op.join.right);
                break;
            case OP_RENAME:
                free(node->op.rename.old_name);
                free(node->op.rename.new_name);
                free_relnode(node->op.rename.input);
                break;
            case OP_GROUPBY:
                free_columns(node->op.groupby.group_cols);
                free_condition(node->op.groupby.having_cond);
                free_relnode(node->op.groupby.input);
                break;
            case OP_SUBQUERY:
                free(node->op.subquery.alias);
                free_relnode(node->op.subquery.subquery);
                break;
            default:
                break;
        }
    }
    free(node);
}

//Step 18: Entry point
int main(int argc, char *argv[]) {
    if (argc > 1) {
        yyin = fopen(argv[1], "r");
        if (yyin == NULL) {
            fprintf(stderr, "Error: cannot open file %s\n", argv[1]);
            return 1;
        }
    }
    yyparse();
    if (result != NULL) {
        print_ra_tree_json(result);
        free_relnode(result);
    }
    if (argc > 1 && yyin != NULL) fclose(yyin);
    return 0;
}
