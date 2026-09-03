import os
import json
import glob
import shutil
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import chromadb

# Ensure environment variables are dynamically reloaded when .env changes
load_dotenv(override=True)

BASE_DIR = Path(__file__).parent
CHUNKS_DIR = BASE_DIR.parent / "buoi_05" / "output" / "chunks"
DB_DIR = BASE_DIR / "storage"
LOCAL_DB_PATH = DB_DIR / "rag_store.db"


def _get_api_key():
    load_dotenv(override=True)
    return os.getenv("GEMINI_API_KEY", "").strip()


def _get_db_conn():
    load_dotenv(override=True)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    dbname = os.getenv("POSTGRES_DB", "rag_db")

    try:
        import psycopg
        conn = psycopg.connect(
            host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=2
        )
        return "postgres", conn
    except Exception:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(LOCAL_DB_PATH)
        return "sqlite", conn


def _init_db():
    db_type, conn = _get_db_conn()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id VARCHAR PRIMARY KEY,
                text TEXT,
                source VARCHAR,
                strategy VARCHAR,
                page_start INT,
                page_end INT
            );
        """)
        conn.commit()
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                text TEXT,
                source TEXT,
                strategy TEXT,
                page_start INTEGER,
                page_end INTEGER
            );
        """)
        conn.commit()
    conn.close()


def _get_chroma_collection(force_reset=False):
    storage_dir = DB_DIR / "chroma"
    storage_dir.mkdir(parents=True, exist_ok=True)

    if force_reset and storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)
        storage_dir.mkdir(parents=True, exist_ok=True)

    try:
        chroma_client = chromadb.PersistentClient(path=str(storage_dir))
        return chroma_client.get_or_create_collection(name="rag_chunks")
    except Exception:
        if storage_dir.exists():
            shutil.rmtree(storage_dir, ignore_errors=True)
        storage_dir.mkdir(parents=True, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=str(storage_dir))
        return chroma_client.get_or_create_collection(name="rag_chunks")


def _embed_text(text: str):
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        try:
            res = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=384)
            )
            return res.embeddings[0].values
        except Exception:
            res = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=384)
            )
            return res.embeddings[0].values
    except Exception:
        return None


def index():
    _init_db()
    try:
        collection = _get_chroma_collection()
    except Exception:
        collection = _get_chroma_collection(force_reset=True)

    json_files = glob.glob(str(CHUNKS_DIR / "*.json"))
    all_chunks = []

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_chunks.extend(data)

    if not all_chunks:
        return {"indexed_chunks": 0}

    db_type, conn = _get_db_conn()
    cur = conn.cursor()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for item in all_chunks:
        chunk_id = item["chunk_id"]
        text = item.get("text", "")
        source = item.get("source", "")
        strategy = item.get("strategy", "")
        page_start = item.get("page_start", 0)
        page_end = item.get("page_end", 0)

        # Save content & metadata to PostgreSQL / SQLite
        if db_type == "postgres":
            cur.execute("""
                INSERT INTO chunks (chunk_id, text, source, strategy, page_start, page_end)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET 
                    text = EXCLUDED.text,
                    source = EXCLUDED.source,
                    strategy = EXCLUDED.strategy,
                    page_start = EXCLUDED.page_start,
                    page_end = EXCLUDED.page_end;
            """, (chunk_id, text, source, strategy, page_start, page_end))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO chunks (chunk_id, text, source, strategy, page_start, page_end)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (chunk_id, text, source, strategy, page_start, page_end))

        # ChromaDB preparation
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append({
            "source": source,
            "strategy": strategy,
            "page_start": page_start,
            "page_end": page_end
        })

        emb = _embed_text(text)
        if emb:
            embeddings.append(emb)

    conn.commit()
    conn.close()

    # Save to ChromaDB in batches of 100 with auto-reset on error
    BATCH_SIZE = 100
    for i in range(0, len(ids), BATCH_SIZE):
        b_ids = ids[i : i + BATCH_SIZE]
        b_docs = documents[i : i + BATCH_SIZE]
        b_metas = metadatas[i : i + BATCH_SIZE]
        try:
            if len(embeddings) == len(ids) and len(ids) > 0:
                b_embs = embeddings[i : i + BATCH_SIZE]
                collection.upsert(ids=b_ids, documents=b_docs, embeddings=b_embs, metadatas=b_metas)
            else:
                collection.upsert(ids=b_ids, documents=b_docs, metadatas=b_metas)
        except Exception:
            collection = _get_chroma_collection(force_reset=True)
            if len(embeddings) == len(ids) and len(ids) > 0:
                b_embs = embeddings[i : i + BATCH_SIZE]
                collection.upsert(ids=b_ids, documents=b_docs, embeddings=b_embs, metadatas=b_metas)
            else:
                collection.upsert(ids=b_ids, documents=b_docs, metadatas=b_metas)

    return {"indexed_chunks": len(all_chunks)}


def _fetch_chunks_by_ids(chunk_ids):
    db_type, conn = _get_db_conn()
    cur = conn.cursor()
    chunk_details = []

    if db_type == "postgres":
        cur.execute("""
            SELECT chunk_id, text, source, strategy, page_start, page_end 
            FROM chunks WHERE chunk_id = ANY(%s)
        """, (chunk_ids,))
        rows = {r[0]: r for r in cur.fetchall()}
        for cid in chunk_ids:
            if cid in rows:
                row = rows[cid]
                chunk_details.append({
                    "chunk_id": row[0],
                    "text": row[1],
                    "source": row[2],
                    "strategy": row[3],
                    "page_start": row[4],
                    "page_end": row[5]
                })
    else:
        placeholders = ",".join(["?"] * len(chunk_ids))
        cur.execute(f"""
            SELECT chunk_id, text, source, strategy, page_start, page_end 
            FROM chunks WHERE chunk_id IN ({placeholders})
        """, chunk_ids)
        rows = {r[0]: r for r in cur.fetchall()}
        for cid in chunk_ids:
            if cid in rows:
                row = rows[cid]
                chunk_details.append({
                    "chunk_id": row[0],
                    "text": row[1],
                    "source": row[2],
                    "strategy": row[3],
                    "page_start": row[4],
                    "page_end": row[5]
                })

    conn.close()
    return chunk_details


def ask_with_chunks(question: str, k: int = 3):
    collection = _get_chroma_collection()
    query_emb = _embed_text(question)

    try:
        if query_emb:
            results = collection.query(query_embeddings=[query_emb], n_results=k)
        else:
            results = collection.query(query_texts=[question], n_results=k)
    except Exception:
        collection = _get_chroma_collection(force_reset=True)
        return "Cơ sở dữ liệu vector vừa được tự động làm sạch do file index bị lỗi. Vui lòng bấm nút 'Index Dữ Liệu Chunks' ở Sidebar để tạo lại dữ liệu.", []

    ids = results.get("ids", [[]])[0]
    if not ids:
        return "Không tìm thấy thông tin phù hợp trong dữ liệu.", []

    chunk_details = _fetch_chunks_by_ids(ids)
    
    formatted_contexts = []
    for item in chunk_details:
        meta_info = f"[Source: {item['source']} | Page: {item['page_start']}-{item['page_end']} | Strategy: {item['strategy']}]"
        formatted_contexts.append(f"{meta_info}\n{item['text']}")
        
    context = "\n---\n".join(formatted_contexts)

    api_key = _get_api_key()
    if not api_key:
        answer = f"[Kết quả Retrieval (Thiếu GEMINI_API_KEY, không gọi LLM)]:\n\n{context}"
        return answer, chunk_details

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"Dựa vào ngữ cảnh sau để trả lời câu hỏi:\n\n{context}\n\nCâu hỏi: {question}"
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt
        )
        return response.text, chunk_details
    except Exception as e:
        answer = f"[Lỗi khi gọi Gemini LLM: {e}]\n\nNgữ cảnh đã truy vấn được:\n{context}"
        return answer, chunk_details


def ask(question: str, k: int = 3) -> str:
    answer, _ = ask_with_chunks(question, k=k)
    return answer


def status():
    _init_db()
    db_type, conn = _get_db_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(DISTINCT source), COUNT(*) FROM chunks;")
    res = cur.fetchone()
    num_docs = res[0] if res else 0
    num_chunks = res[1] if res else 0

    conn.close()
    return {
        "documents": num_docs or 0,
        "chunks": num_chunks or 0
    }
