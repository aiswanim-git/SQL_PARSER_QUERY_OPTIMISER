# SQL Parser Query Optimizer

A SQL query optimizer that parses `SELECT` statements into a relational
algebra tree and applies three classic optimization passes: predicate
pushdown, cost-based join reordering, and common subexpression elimination.
The pipeline and each intermediate plan can be inspected in a browser UI.

## Architecture

```
SQL text --(Flex/Bison)--> Relational Algebra JSON --(Flask)--> Optimizer passes --> Visualized plan
```

- **Parser** (`parser/`): Flex + Bison, compiled to a standalone C++ binary
  that reads SQL and prints the relational algebra tree as JSON.
- **Web app** (`web_rule/`): Flask backend that shells out to the parser
  binary, runs the optimization passes, and serves an interactive UI.

Note on the cost model: join-order optimization uses a PostgreSQL-inspired
cost formula (page costs, tuple costs, selectivity estimation) but runs in
**mock mode** by default — table statistics are randomly generated rather
than pulled from a live database. This keeps the demo self-contained; the
`QueryOptimizer` class is structured so a real `psycopg2` connection could
be wired in if needed.

## 1) Install system dependencies

```bash
sudo apt update
sudo apt install -y bison flex g++ python3 python3-venv python3-pip
```

## 2) Build the SQL parser

```bash
cd parser
make
```

Optional quick test:

```bash
echo "SELECT e.name FROM employees e WHERE e.salary > 50000" | ./sql_parser
```

Note: `yywrap()` is defined directly in `sql_tokeniser.l`, so no `-lfl`
link flag is needed — the Makefile's plain
`g++ -o sql_parser y.tab.c lex.yy.c` is correct as-is.

## 3) Run the web app

Open a new terminal from the project root:

```bash
cd web_rule
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 4) Open in browser

```text
http://127.0.0.1:8000
```

Check `http://127.0.0.1:8000/health` to confirm the parser binary was found.

## Notes

- Build the parser first (`parser/sql_parser`) before starting the web app.
- If the parser binary is in a different location, set:

```bash
export SQL_TO_RA_BIN=/absolute/path/to/sql_parser
```

- For a real deployment, set `FLASK_SECRET_KEY` and disable debug mode
  (`FLASK_DEBUG=0`, which is already the default).
