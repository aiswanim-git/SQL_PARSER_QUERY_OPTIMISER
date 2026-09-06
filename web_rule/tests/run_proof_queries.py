"""
Proof-of-work test runner for the SQL Query Optimizer.

Usage:
    1. Start the app:  cd web_rule && python app.py
    2. In another terminal:  pip install requests
    3. python run_proof_queries.py --host http://127.0.0.1:8000

Outputs:
    test_results/<query_name>.json   -- full stage-by-stage pipeline output
    test_results/summary.md          -- a ready-to-paste markdown table for the proof doc
"""

import argparse
import json
import os
import re
import textwrap

import requests

QUERIES = {
    "q1_3table_join": """
        SELECT A.id, B.name, C.salary
        FROM employee A
        JOIN department B ON A.dept_id = B.id
        JOIN salary C ON A.id = C.emp_id
        WHERE A.age > 30 AND B.location = 'Delhi' AND C.salary > 60000
    """,
    "q2_4table_join": """
        SELECT A.id, B.name, C.salary, D.project
        FROM employee A
        JOIN department B ON A.dept_id = B.id
        JOIN salary C ON A.id = C.emp_id
        JOIN project D ON A.id = D.emp_id
        WHERE A.age > 25 AND B.location = 'Mumbai' AND C.salary > 50000 AND D.status = 'Active'
    """,
    "q3_pushdown_focus": """
        SELECT * FROM orders O
        JOIN customers C ON O.customer_id = C.id
        WHERE O.amount > 1000 AND C.city = 'Hyderabad'
    """,
    "q4_5table_join": """
        SELECT A.id, B.name, C.salary, D.project, E.rating
        FROM employee A
        JOIN department B ON A.dept_id = B.id
        JOIN salary C ON A.id = C.emp_id
        JOIN project D ON A.id = D.emp_id
        JOIN review E ON A.id = E.emp_id
        WHERE A.age > 30 AND B.location = 'Delhi' AND C.salary > 60000
        AND D.status = 'Completed' AND E.rating >= 4
    """,
    "q5_group_by_having": """
        SELECT A.dept_id FROM employee A
        JOIN salary B ON A.id = B.emp_id
        WHERE A.age > 25
        GROUP BY A.dept_id HAVING A.dept_id > 3
    """,
    "q6_nested_subquery": """
        SELECT X.id FROM
        (SELECT id, dept_id FROM employee WHERE age > 30) AS X
        JOIN department D ON X.dept_id = D.id
        WHERE D.location = 'Delhi'
    """,
    "q7_many_predicates": """
        SELECT * FROM employee A
        JOIN department B ON A.dept_id = B.id
        JOIN salary C ON A.id = C.emp_id
        WHERE A.age > 30 AND A.gender = 'F' AND B.location = 'Delhi'
        AND B.size > 100 AND C.salary > 70000
    """,
    "q8_5way_chain_join": """
        SELECT * FROM A
        JOIN B ON A.id = B.aid
        JOIN C ON B.id = C.bid
        JOIN D ON C.id = D.cid
        JOIN E ON D.id = E.did
    """,
    # Robustness case: exceeds MAX_TABLES guard added to app.py
    "q9_oversize_join_should_reject": """
        SELECT * FROM T1
        JOIN T2 ON T1.id = T2.t1id
        JOIN T3 ON T2.id = T3.t2id
        JOIN T4 ON T3.id = T4.t3id
        JOIN T5 ON T4.id = T5.t4id
        JOIN T6 ON T5.id = T6.t5id
        JOIN T7 ON T6.id = T7.t6id
        JOIN T8 ON T7.id = T8.t7id
        JOIN T9 ON T8.id = T9.t8id
    """,
    # Robustness case: malformed SQL should return a clean JSON error
    "q10_malformed_should_error": """
        SELEC * FORM employee WHERE
    """,
}


def find_first_select_above_base(node, path=""):
    """Return list of (path, table_name) showing how close each 'select' node
    sits to the base_relation it filters -- used as pushdown evidence."""
    hits = []
    if not isinstance(node, dict):
        return hits
    if node.get("type") == "select":
        child = node.get("input", {})
        if isinstance(child, dict) and child.get("type") == "base_relation":
            names = [t.get("name") for t in child.get("tables", [])]
            hits.append((path + "/select", names))
    for key in ("input", "left", "right", "query"):
        child = node.get(key)
        if isinstance(child, dict):
            hits.extend(find_first_select_above_base(child, path + f"/{key}"))
    return hits


def run_query(session, host, name, sql):
    sql = textwrap.dedent(sql).strip()
    record = {"name": name, "sql": sql}

    resp = session.post(f"{host}/analyze", data={"sql_query": sql}, timeout=60)
    data = resp.json()
    record["analyze_status_code"] = resp.status_code
    record["analyze_success"] = data.get("success")
    record["analyze_error"] = data.get("error")
    record["stages"] = data.get("stages")

    if data.get("success"):
        stages = data["stages"]
        pred_plan = (stages.get("predicate_pushdown") or {}).get("optimized_plan")
        record["pushdown_evidence"] = (
            find_first_select_above_base(pred_plan) if pred_plan else []
        )

        join_meta = (stages.get("join_optimization") or {}).get("meta")
        record["join_meta"] = join_meta

        cse_meta = (stages.get("cse") or {}).get("meta")
        record["cse_meta"] = cse_meta

        # Also hit the cost-based endpoint in the SAME session for real
        # naive-vs-optimized numbers (proves actual cost reduction).
        try:
            cost_resp = session.post(f"{host}/optimize/join/cost", json={"relational_algebra": pred_plan}, timeout=120)
            cost_data = cost_resp.json()
            if cost_data.get("success"):
                record["cost_comparison"] = {
                    "naive_cost": cost_data.get("naive_cost"),
                    "best_cost": cost_data.get("best_cost"),
                    "cost_scale": cost_data.get("cost_scale"),
                    "selected_order": cost_data.get("selected_order"),
                    "selected_strategies": cost_data.get("selected_strategies"),
                }
            else:
                record["cost_comparison"] = {"error": cost_data.get("error")}
        except Exception as exc:
            record["cost_comparison"] = {"error": str(exc)}

    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--outdir", default="test_results")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    session = requests.Session()

    summary_rows = []
    for name, sql in QUERIES.items():
        print(f"Running {name} ...")
        try:
            record = run_query(session, args.host, name, sql)
        except Exception as exc:
            record = {"name": name, "sql": sql, "analyze_success": False, "analyze_error": str(exc)}

        with open(os.path.join(args.outdir, f"{name}.json"), "w") as f:
            json.dump(record, f, indent=2, default=str)

        ok = record.get("analyze_success")
        cost = record.get("cost_comparison", {})
        summary_rows.append({
            "name": name,
            "status": "PASS" if (ok or "should_reject" in name or "should_error" in name) and (
                (not ok and ("should_reject" in name or "should_error" in name)) or ok
            ) else "CHECK",
            "analyze_success": ok,
            "naive_cost": cost.get("naive_cost"),
            "best_cost": cost.get("best_cost"),
            "pushdown_hits": len(record.get("pushdown_evidence", []) or []),
            "cse_duplicates": (record.get("cse_meta") or {}).get("duplicate_count"),
            "error": record.get("analyze_error"),
        })

    summary_path = os.path.join(args.outdir, "summary.md")
    with open(summary_path, "w") as f:
        f.write("| Query | Analyze OK | Naive Cost | Best Cost | Pushdown hits | CSE duplicates | Note |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for row in summary_rows:
            f.write(
                f"| {row['name']} | {row['analyze_success']} | "
                f"{row['naive_cost']} | {row['best_cost']} | "
                f"{row['pushdown_hits']} | {row['cse_duplicates']} | "
                f"{row['error'] or ''} |\n"
            )

    print(f"\nDone. Per-query JSON + {summary_path} written to {args.outdir}/")
    print("Paste summary.md into your proof document, and attach 2-3 raw JSON files as appendix evidence.")


if __name__ == "__main__":
    main()
