from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
auth = ("neo4j", "abcd1234")

driver = GraphDatabase.driver(uri, auth=auth)

# Check if multi-database creation is supported
with driver.session(database="system") as session:
    try:
        session.run("CREATE DATABASE `kb-hops` IF NOT EXISTS")
        print("[+] Successfully created database `kb-hops`")
    except Exception as e:
        print("[!] Note on database creation:", e)

with driver.session() as session:
    res = session.run("SHOW DATABASES")
    for r in res:
        print(f"  - Database: {r['name']}, State: {r.get('currentStatus', 'N/A')}")

driver.close()
