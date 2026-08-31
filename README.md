# SQL Parser Query Optimizer

Simple instructions to run the project on Linux.

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

## Notes

- Build the parser first (`parser/sql_parser`) before starting the web app.
- If the parser binary is in a different location, set:

```bash
export SQL_TO_RA_BIN=/absolute/path/to/sql_parser
```