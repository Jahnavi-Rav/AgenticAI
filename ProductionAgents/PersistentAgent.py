import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List


DB_PATH = "agent_store.db"
OBJECT_DIR = Path("object_storage")


def now() -> float:
    return time.time()


def canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def checksum(data: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def simple_embedding(text: str) -> List[float]:
    """
    Toy embedding for learning.
    Real systems use OpenAI embeddings, sentence-transformers, etc.
    """
    vector = [0.0] * 10

    for word in text.lower().split():
        index = sum(ord(c) for c in word) % len(vector)
        vector[index] += 1.0

    return vector


class MigrationManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def setup_migration_table(self) -> None:
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at REAL NOT NULL
        )
        """)
        self.conn.commit()

    def applied_versions(self) -> set[int]:
        rows = self.conn.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()

        return {row[0] for row in rows}

    def apply_migrations(self) -> None:
        self.setup_migration_table()

        migrations = {
            1: [
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    event TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS object_storage (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """,
            ]
        }

        applied = self.applied_versions()

        for version, statements in migrations.items():
            if version in applied:
                continue

            try:
                self.conn.execute("BEGIN")

                for statement in statements:
                    self.conn.execute(statement)

                self.conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, now()),
                )

                self.conn.commit()
                print(f"Migration {version} applied.")

            except Exception as e:
                self.conn.rollback()
                raise RuntimeError(f"Migration {version} failed and was rolled back: {e}")

    def simulate_bad_migration(self) -> None:
        """
        Demonstrates protection against migration bugs.
        This intentionally fails and rolls back.
        """
        try:
            self.conn.execute("BEGIN")
            self.conn.execute("CREATE TABL broken_sql (id TEXT)")
            self.conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (999, now()),
            )
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print("Bad migration blocked and rolled back:", e)


class AgentStore:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        OBJECT_DIR.mkdir(exist_ok=True)

        MigrationManager(self.conn).apply_migrations()

    # -------------------------
    # Memory storage
    # -------------------------

    def add_memory(self, text: str) -> str:
        if not text.strip():
            raise ValueError("Memory text cannot be empty.")

        memory_id = str(uuid.uuid4())
        created_at = now()
        embedding = simple_embedding(text)

        record = {
            "id": memory_id,
            "text": text,
            "embedding": embedding,
            "created_at": created_at,
        }

        self.conn.execute(
            """
            INSERT INTO memories(id, text, embedding_json, checksum, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                text,
                json.dumps(embedding),
                checksum(record),
                created_at,
            ),
        )

        self.conn.commit()
        return memory_id

    def list_memories(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM memories").fetchall()

        return [
            {
                "id": row["id"],
                "text": row["text"],
                "embedding": json.loads(row["embedding_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    # -------------------------
    # Task storage
    # -------------------------

    def create_task(self, payload: Dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        created_at = now()
        updated_at = created_at
        status = "queued"

        record = {
            "id": task_id,
            "status": status,
            "payload": payload,
            "created_at": created_at,
            "updated_at": updated_at,
        }

        self.conn.execute(
            """
            INSERT INTO tasks(id, status, payload_json, checksum, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                status,
                json.dumps(payload),
                checksum(record),
                created_at,
                updated_at,
            ),
        )

        self.conn.commit()
        return task_id

    def update_task(self, task_id: str, status: str, payload: Dict[str, Any]) -> None:
        row = self.conn.execute(
            "SELECT created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if not row:
            raise ValueError("Task not found.")

        updated_at = now()

        record = {
            "id": task_id,
            "status": status,
            "payload": payload,
            "created_at": row["created_at"],
            "updated_at": updated_at,
        }

        self.conn.execute(
            """
            UPDATE tasks
            SET status = ?, payload_json = ?, checksum = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(payload),
                checksum(record),
                updated_at,
                task_id,
            ),
        )

        self.conn.commit()

    # -------------------------
    # Trace storage
    # -------------------------

    def add_trace(self, task_id: str, event: str, metadata: Dict[str, Any]) -> str:
        trace_id = str(uuid.uuid4())
        created_at = now()

        record = {
            "id": trace_id,
            "task_id": task_id,
            "event": event,
            "metadata": metadata,
            "created_at": created_at,
        }

        self.conn.execute(
            """
            INSERT INTO traces(id, task_id, event, metadata_json, checksum, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                task_id,
                event,
                json.dumps(metadata),
                checksum(record),
                created_at,
            ),
        )

        self.conn.commit()
        return trace_id

    # -------------------------
    # Object storage
    # -------------------------

    def store_object(self, name: str, content: bytes) -> str:
        object_id = str(uuid.uuid4())
        safe_name = name.replace("/", "_").replace("..", "_")
        path = OBJECT_DIR / f"{object_id}_{safe_name}"

        path.write_bytes(content)

        digest = hashlib.sha256(content).hexdigest()

        self.conn.execute(
            """
            INSERT INTO object_storage(id, path, checksum, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (object_id, str(path), digest, now()),
        )

        self.conn.commit()
        return object_id

    def read_object(self, object_id: str) -> bytes:
        row = self.conn.execute(
            "SELECT path, checksum FROM object_storage WHERE id = ?",
            (object_id,),
        ).fetchone()

        if not row:
            raise ValueError("Object not found.")

        data = Path(row["path"]).read_bytes()
        actual = hashlib.sha256(data).hexdigest()

        if actual != row["checksum"]:
            raise ValueError("Data corruption detected in object storage.")

        return data

    # -------------------------
    # Corruption detection
    # -------------------------

    def verify_integrity(self) -> List[str]:
        issues = []

        memory_rows = self.conn.execute("SELECT * FROM memories").fetchall()

        for row in memory_rows:
            record = {
                "id": row["id"],
                "text": row["text"],
                "embedding": json.loads(row["embedding_json"]),
                "created_at": row["created_at"],
            }

            if checksum(record) != row["checksum"]:
                issues.append(f"Corrupted memory row: {row['id']}")

        task_rows = self.conn.execute("SELECT * FROM tasks").fetchall()

        for row in task_rows:
            record = {
                "id": row["id"],
                "status": row["status"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

            if checksum(record) != row["checksum"]:
                issues.append(f"Corrupted task row: {row['id']}")

        trace_rows = self.conn.execute("SELECT * FROM traces").fetchall()

        for row in trace_rows:
            record = {
                "id": row["id"],
                "task_id": row["task_id"],
                "event": row["event"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }

            if checksum(record) != row["checksum"]:
                issues.append(f"Corrupted trace row: {row['id']}")

        object_rows = self.conn.execute("SELECT * FROM object_storage").fetchall()

        for row in object_rows:
            path = Path(row["path"])

            if not path.exists():
                issues.append(f"Missing object file: {row['id']}")
                continue

            actual = hashlib.sha256(path.read_bytes()).hexdigest()

            if actual != row["checksum"]:
                issues.append(f"Corrupted object file: {row['id']}")

        return issues

    def simulate_memory_corruption(self) -> None:
        row = self.conn.execute("SELECT id FROM memories LIMIT 1").fetchone()

        if not row:
            print("No memory available to corrupt.")
            return

        self.conn.execute(
            "UPDATE memories SET text = ? WHERE id = ?",
            ("CORRUPTED MEMORY TEXT", row["id"]),
        )

        self.conn.commit()
        print("Simulated memory corruption.")


if __name__ == "__main__":
    store = AgentStore()

    print("\nAdding memory...")
    memory_id = store.add_memory("User is learning Agentic AI persistence.")
    print("Memory ID:", memory_id)

    print("\nCreating task...")
    task_id = store.create_task({
        "goal": "Summarize persistence systems",
        "priority": "normal",
    })
    print("Task ID:", task_id)

    print("\nAdding traces...")
    store.add_trace(task_id, "task_created", {"status": "queued"})
    store.update_task(task_id, "completed", {"result": "Persistence summary complete"})
    store.add_trace(task_id, "task_completed", {"status": "completed"})

    print("\nStoring object...")
    object_id = store.store_object(
        "notes.txt",
        b"These are agent persistence notes."
    )
    print("Object ID:", object_id)

    print("\nReading object...")
    print(store.read_object(object_id).decode("utf-8"))

    print("\nIntegrity check before corruption:")
    issues = store.verify_integrity()
    print(issues if issues else "No corruption detected.")

    print("\nSimulating corruption...")
    store.simulate_memory_corruption()

    print("\nIntegrity check after corruption:")
    issues = store.verify_integrity()
    print(issues if issues else "No corruption detected.")

    print("\nSimulating bad migration...")
    MigrationManager(store.conn).simulate_bad_migration()