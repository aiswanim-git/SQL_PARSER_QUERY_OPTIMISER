%{
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
%}

%union {
    int intval;
    float floatval;
    char *strval;
    struct Column *col;
    struct Table *tbl;
    struct Condition *cond;
    struct RelNode *node;
}

//Step 4: Declare typed tokens and non-terminals
%token <strval> IDENTIFIER
%token <intval> INT_LITERAL
%token <floatval> FLOAT_LITERAL
%token <strval> STRING_LITERAL

%token SELECT FROM WHERE JOIN ON AS AND OR NOT GROUP BY HAVING

%token EQ LT GT LEQ GEQ NEQ

%type <col>  column_list column
%type <tbl>  table_ref
%type <cond> opt_where_clause where_clause condition comparison_expr join_condition
%type <cond> opt_having_clause
%type <col>  opt_group_by group_by_cols
%type <node> query_stmt join_list join_table table_item subquery
%type <strval> dotted_identifier

//Step 5: Declare operator precedence (lowest to highest)
%left OR
%left AND
%right NOT

%%

//Step 6: Grammar rules

start:
    query_stmt {
        result = $1;
    }
;

query_stmt:
    SELECT column_list FROM join_list opt_where_clause opt_group_by opt_having_clause {
        //Step 6a: Build the base project node over the join list
        RelNode *base = $4;

        //Step 6b: Apply WHERE selection if present
        if ($5 != NULL) {
            base = create_select_node(base, $5);
        }

        //Step 6c: Apply GROUP BY with optional HAVING if present
        if ($6 != NULL) {
            base = create_groupby_node(base, $6, $7);
        }

        //Step 6d: Apply projection of column list
        $$ = create_project_node(base, $2);
    }
;

//Step 7: Column list rules
column_list:
    column {
        $$ = $1;
    }
    | column_list ',' column {
        $$ = append_column($1, $3);
    }
;

column:
    IDENTIFIER '.' dotted_identifier {
        $$ = create_column($1, $3);
        free($1);
        free($3);
    }
    | IDENTIFIER '.' '*' {
        $$ = create_column($1, strdup("*"));
        free($1);
    }
    | '*' {
        $$ = create_column(strdup("*"), strdup("*"));
    }
;

dotted_identifier:
    IDENTIFIER {
        $$ = strdup($1);
        free($1);
    }
    | dotted_identifier '.' IDENTIFIER {
        char *temp = (char *)malloc(strlen($1) + strlen($3) + 2);
        sprintf(temp, "%s.%s", $1, $3);
        $$ = temp;
        free($1);
        free($3);
    }
;

//Step 8: Join list rules
join_list:
    table_item {
        $$ = $1;
    }
    | join_list JOIN join_table ON join_condition {
        $$ = create_join_node($1, $3, $5);
    }
;

join_table:
    table_item {
        $$ = $1;
    }
;

table_item:
    table_ref {
        $$ = create_base_relation($1);
    }
    | subquery {
        $$ = $1;
    }
;

subquery:
    '(' query_stmt ')' AS IDENTIFIER {
        $$ = create_subquery_node($2, $5);
        free($5);
    }
    | '(' query_stmt ')' IDENTIFIER {
        //Step 8a: Implicit AS for subquery alias
        $$ = create_subquery_node($2, $4);
        free($4);
    }
;

table_ref:
    IDENTIFIER {
        $$ = create_table($1, NULL);
        free($1);
    }
    | IDENTIFIER AS IDENTIFIER {
        $$ = create_table($1, $3);
        free($1);
        free($3);
    }
    | IDENTIFIER IDENTIFIER {
        //Step 8b: Implicit AS for table alias
        $$ = create_table($1, $2);
        free($1);
        free($2);
    }
;

//Step 9: Optional WHERE clause
opt_where_clause:
    /* empty */ {
        $$ = NULL;
    }
    | where_clause {
        $$ = $1;
    }
;

where_clause:
    WHERE condition {
        $$ = $2;
    }
;

//Step 10: Optional GROUP BY clause
opt_group_by:
    /* empty */ {
        $$ = NULL;
    }
    | GROUP BY group_by_cols {
        $$ = $3;
    }
;

group_by_cols:
    column {
        $$ = $1;
    }
    | group_by_cols ',' column {
        $$ = append_column($1, $3);
    }
;

//Step 11: Optional HAVING clause
opt_having_clause:
    /* empty */ {
        $$ = NULL;
    }
    | HAVING condition {
        $$ = $2;
    }
;

join_condition:
    condition {
        $$ = $1;
    }
;

//Step 12: Condition rules with AND / OR / NOT and parentheses
condition:
    comparison_expr {
        $$ = $1;
    }
    | condition AND condition {
        $$ = create_binary_condition(COND_AND, $1, $3);
    }
    | condition OR condition {
        $$ = create_binary_condition(COND_OR, $1, $3);
    }
    | NOT condition {
        $$ = create_unary_condition(COND_NOT, $2);
    }
    | '(' condition ')' {
        $$ = $2;
    }
;

//Step 13: Comparison expression rules for all operator/operand combinations
comparison_expr:
    IDENTIFIER '.' dotted_identifier EQ IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_EQ, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier LT IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_LT, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier GT IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_GT, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier LEQ IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_LE, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier GEQ IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_GE, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier NEQ IDENTIFIER '.' dotted_identifier {
        $$ = create_comparison(COND_NE, $1, $3, 3, 0, 0.0, NULL, $5, $7);
        free($1); free($3); free($5); free($7);
    }
    | IDENTIFIER '.' dotted_identifier EQ INT_LITERAL {
        $$ = create_comparison(COND_EQ, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier LT INT_LITERAL {
        $$ = create_comparison(COND_LT, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier GT INT_LITERAL {
        $$ = create_comparison(COND_GT, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier LEQ INT_LITERAL {
        $$ = create_comparison(COND_LE, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier GEQ INT_LITERAL {
        $$ = create_comparison(COND_GE, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier NEQ INT_LITERAL {
        $$ = create_comparison(COND_NE, $1, $3, 0, $5, 0.0, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier EQ FLOAT_LITERAL {
        $$ = create_comparison(COND_EQ, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier LT FLOAT_LITERAL {
        $$ = create_comparison(COND_LT, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier GT FLOAT_LITERAL {
        $$ = create_comparison(COND_GT, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier LEQ FLOAT_LITERAL {
        $$ = create_comparison(COND_LE, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier GEQ FLOAT_LITERAL {
        $$ = create_comparison(COND_GE, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier NEQ FLOAT_LITERAL {
        $$ = create_comparison(COND_NE, $1, $3, 1, 0, $5, NULL, NULL, NULL);
        free($1); free($3);
    }
    | IDENTIFIER '.' dotted_identifier EQ STRING_LITERAL {
        $$ = create_comparison(COND_EQ, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
    | IDENTIFIER '.' dotted_identifier LT STRING_LITERAL {
        $$ = create_comparison(COND_LT, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
    | IDENTIFIER '.' dotted_identifier GT STRING_LITERAL {
        $$ = create_comparison(COND_GT, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
    | IDENTIFIER '.' dotted_identifier LEQ STRING_LITERAL {
        $$ = create_comparison(COND_LE, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
    | IDENTIFIER '.' dotted_identifier GEQ STRING_LITERAL {
        $$ = create_comparison(COND_GE, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
    | IDENTIFIER '.' dotted_identifier NEQ STRING_LITERAL {
        $$ = create_comparison(COND_NE, $1, $3, 2, 0, 0.0, $5, NULL, NULL);
        free($1); free($3); free($5);
    }
;

%%

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