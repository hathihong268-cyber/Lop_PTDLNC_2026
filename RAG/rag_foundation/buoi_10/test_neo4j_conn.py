import sys
from neo4j import GraphDatabase, exceptions

common_passwords = ["abcd1234", "12345678", "neo4j", "password", "password123", "123456"]
uri = "neo4j://127.0.0.1:7687"
user = "neo4j"

for pwd in common_passwords:
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd), connection_timeout=3.0)
        driver.verify_connectivity()
        print(f"[SUCCESS] Connected to Neo4j successfully with username='{user}' and password='{pwd}'!")
        
        with driver.session() as session:
            try:
                res = session.run("SHOW DATABASES")
                dbs = [r["name"] for r in res]
                print(f"[INFO] Current databases: {dbs}")
            except Exception as e:
                print(f"[INFO] SHOW DATABASES note: {e}")
        driver.close()
        sys.exit(0)
    except exceptions.AuthError:
        print(f"[-] Password '{pwd}' incorrect.")
    except Exception as e:
        print(f"[-] Connection attempt failed for '{pwd}': {e}")

print("[!] Could not connect with common passwords. A custom password might be set.")
