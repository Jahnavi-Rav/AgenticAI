import sqlite3
import re
from typing import Optional


ALLOWED_TABLES = {
    "customers": ["id", "name", "city"],
    "orders": ["id", "customer_id", "amount", "year"],
}

ALLOWED_JOINS = {
    ("customers", "orders"): "customers.id = orders.customer_id",
}


def setup_db():
    conn = sqlite3.connect("shop.db")
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS customers")
    cur.execute("DROP TABLE IF EXISTS orders")

    cur.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT,
        city TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount REAL,
        year INTEGER,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """)

    cur.executemany("INSERT INTO customers VALUES (?, ?, ?)", [
        (1, "Jenny", "New York"),
        (2, "Alex", "London"),
        (3, "Maya", "Mumbai"),
    ])

    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", [
        (1, 1, 250.0, 2024),
        (2, 1, 150.0, 2025),
        (3, 2, 300.0, 2024),
        (4, 3, 500.0, 2025),
    ])

    conn.commit()
    return conn


def contains_sql_injection(text: str) -> bool:
    dangerous = [
        ";",
        "--",
        "drop",
        "delete",
        "insert",
        "update",
        "alter",
        "truncate",
        "pragma",
    ]

    lowered = text.lower()
    return any(word in lowered for word in dangerous)


def nl_to_sql(question: str) -> Optional[str]:
    q = question.lower()

    if contains_sql_injection(q):
        return None

    if "total sales" in q or "total orders" in q:
        if "2024" in q:
            return "SELECT SUM(amount) FROM orders WHERE year = 2024"
        if "2025" in q:
            return "SELECT SUM(amount) FROM orders WHERE year = 2025"
        return "SELECT SUM(amount) FROM orders"

    if "customers" in q and "orders" in q:
        return """
        SELECT customers.name, orders.amount, orders.year
        FROM customers
        JOIN orders ON customers.id = orders.customer_id
        """

    if "customers" in q:
        return "SELECT name, city FROM customers"

    if "orders" in q:
        return "SELECT id, customer_id, amount, year FROM orders"

    return None


def extract_columns(sql: str):
    match = re.search(r"select\s+(.*?)\s+from", sql, re.IGNORECASE | re.DOTALL)

    if not match:
        return []

    cols = match.group(1).strip()

    if cols == "*":
        return ["*"]

    return [
        col.strip().split(" AS ")[0].strip()
        for col in cols.split(",")
    ]


def validate_sql(sql: str) -> Optional[str]:
    lowered = sql.lower().strip()

    if not lowered.startswith("select"):
        return "Blocked: only SELECT queries are allowed."

    if contains_sql_injection(lowered):
        return "Blocked: possible SQL injection."

    used_tables = [
        table for table in ALLOWED_TABLES
        if re.search(rf"\b{table}\b", lowered)
    ]

    if not used_tables:
        return "Blocked: no allowed table found."

    # Detect hallucinated columns
    selected_columns = extract_columns(sql)

    for col in selected_columns:
        if col == "*" or col.lower().startswith("sum("):
            continue

        if "." in col:
            table, column = col.split(".", 1)
            if table not in ALLOWED_TABLES or column not in ALLOWED_TABLES[table]:
                return f"Blocked: hallucinated column '{col}'."
        else:
            valid = any(col in columns for columns in ALLOWED_TABLES.values())
            if not valid:
                return f"Blocked: hallucinated column '{col}'."

    # Detect wrong joins
    if "join" in lowered:
        if "customers" in used_tables and "orders" in used_tables:
            correct_join = ALLOWED_JOINS[("customers", "orders")]
            if correct_join not in sql:
                return "Blocked: wrong join condition."
        else:
            return "Blocked: unsupported join."

    return None


def execute_sql(conn, sql: str):
    error = validate_sql(sql)

    if error:
        return error

    try:
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        return f"SQL execution error: {e}"


def ask_agent(conn, question: str):
    sql = nl_to_sql(question)

    if sql is None:
        return {
            "sql": None,
            "result": "Could not safely convert question to SQL.",
        }

    result = execute_sql(conn, sql)

    return {
        "sql": sql.strip(),
        "result": result,
    }


if __name__ == "__main__":
    conn = setup_db()

    tests = [
        "What are total sales in 2024?",
        "Show customers and orders",
        "Show customers",
        "DROP TABLE customers;",
        "Show customer emails",
    ]

    for question in tests:
        print("\nQuestion:", question)

        output = ask_agent(conn, question)

        print("SQL:", output["sql"])
        print("Result:", output["result"])