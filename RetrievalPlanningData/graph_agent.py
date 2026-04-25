import kuzu
from typing import Optional, List, Dict


DB_PATH = "./agent_graph_db"


def setup_db():
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    conn.execute("""
    CREATE NODE TABLE IF NOT EXISTS Entity(
        name STRING,
        type STRING,
        aliases STRING,
        PRIMARY KEY(name)
    )
    """)

    conn.execute("""
    CREATE REL TABLE IF NOT EXISTS RELATES(
        FROM Entity TO Entity,
        relation STRING
    )
    """)

    return conn


def add_entity(conn, name: str, type_: str, aliases: str = ""):
    conn.execute(
        "MERGE (e:Entity {name: $name}) "
        "SET e.type = $type, e.aliases = $aliases",
        {"name": name, "type": type_, "aliases": aliases},
    )


def add_relation(conn, source: str, relation: str, target: str):
    conn.execute(
        """
        MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
        MERGE (a)-[:RELATES {relation: $relation}]->(b)
        """,
        {"source": source, "relation": relation, "target": target},
    )


def seed_graph(conn):
    add_entity(conn, "Apple Inc.", "Company", "apple,iphone maker")
    add_entity(conn, "Apple", "Fruit", "apple fruit")
    add_entity(conn, "Agent", "AI Concept", "ai agent")
    add_entity(conn, "Tools", "AI Concept", "functions,apis")
    add_entity(conn, "Memory", "AI Concept", "state,recall")

    add_relation(conn, "Apple Inc.", "makes", "Tools")
    add_relation(conn, "Agent", "uses", "Tools")
    add_relation(conn, "Agent", "has", "Memory")


def find_entity(conn, user_text: str) -> Optional[Dict]:
    """
    Handles incorrect entity linking:
    - exact match first
    - alias match second
    - if multiple matches, asks for clarification
    """

    text = user_text.lower()

    result = conn.execute(
        """
        MATCH (e:Entity)
        RETURN e.name, e.type, e.aliases
        """
    )

    matches = []

    while result.has_next():
        row = result.get_next()
        name, type_, aliases = row

        searchable = f"{name} {aliases}".lower()

        if text in searchable or name.lower() in text:
            matches.append({
                "name": name,
                "type": type_,
                "aliases": aliases,
            })

    if len(matches) == 0:
        return None

    if len(matches) > 1:
        print("\nAmbiguous entity found:")
        for i, match in enumerate(matches, start=1):
            print(f"{i}. {match['name']} ({match['type']})")

        choice = input("Choose entity number, or press Enter to cancel: ").strip()

        if not choice.isdigit():
            return None

        index = int(choice) - 1

        if index < 0 or index >= len(matches):
            return None

        return matches[index]

    return matches[0]


def get_facts(conn, entity_name: str) -> List[str]:
    result = conn.execute(
        """
        MATCH (a:Entity {name: $name})-[r:RELATES]->(b:Entity)
        RETURN a.name, r.relation, b.name
        """,
        {"name": entity_name},
    )

    facts = []

    while result.has_next():
        s, r, o = result.get_next()
        facts.append(f"{s} --{r}--> {o}")

    return facts


def graph_agent(conn, question: str):
    entity = find_entity(conn, question)

    if entity is None:
        return {
            "answer": "I don't know. I could not confidently link the entity.",
            "edge_case": "incorrect_entity_linking_or_unknown_entity",
        }

    facts = get_facts(conn, entity["name"])

    if not facts:
        return {
            "answer": f"I found the entity '{entity['name']}', but the graph has no related facts.",
            "edge_case": "graph_gap",
        }

    return {
        "answer": f"Facts about {entity['name']}:\n" + "\n".join(facts),
        "edge_case": None,
    }


if __name__ == "__main__":
    conn = setup_db()
    seed_graph(conn)

    print("Graph Agent over Kùzu")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("Ask: ").strip()

        if question.lower() in ["exit", "quit"]:
            break

        result = graph_agent(conn, question)

        print("\nAnswer:")
        print(result["answer"])

        if result["edge_case"]:
            print("Edge case:", result["edge_case"])

        print()