# Buoi 08: Advanced RAG - Hybrid Search & Cross-Encoder Reranking

> **Khong phai tu van phap ly.** Day la du an hoc thuat nghien cuu ky thuat RAG tren van ban phap luat.

---

## 1. Muc tieu & Khac biet Buoi 07 / Buoi 08

| Tieu chi | Buoi 07 (Baseline) | Buoi 08 (Advanced RAG) |
|---|---|---|
| Retrieval | Semantic only (Chroma + Gemini Embedding) | BM25 + Semantic -> RRF -> Cross-Encoder Rerank |
| Xu ly tu khoa | Embedding an | Tokenizer tach tu phap ly tieng Viet (Unicode NFC) |
| Ket hop ket qua | Khong | Reciprocal Rank Fusion (RRF) |
| Re-ranking | Khong | Cross-Encoder BAAI/bge-reranker-v2-m3 |
| Confidence gate | Cosine distance | Cosine distance (semantic) + Rerank score (hybrid_rerank) |
| Compare modes | Khong | CLI so sanh BM25 / Semantic / Hybrid / Hybrid+Rerank |
| UI | Tab don | 4 tab: Hoi dap, So sanh, Pipeline Trace, Danh gia |
| Metrics | Khong | Recall@K, MRR@K, nDCG@K, Latency |

---

## 2. So do Pipeline

```
                    ┌─────────────────┐
   Question ──────> │  BM25 Retrieval │ ──> N candidates (sparse/lexical)
                    └─────────────────┘         │
                                                 ├──> Reciprocal Rank Fusion (RRF)
   Question ──────> │ Semantic Retrieval│ ──> M candidates (dense/vector)
                    └──────────────────┘         │
                                                 ↓
                              ┌──────────────────────────┐
                              │  Fused candidates (union) │
                              └──────────────────────────┘
                                           │
                              ┌────────────▼──────────────┐
                              │ Cross-Encoder Reranker      │
                              │ BAAI/bge-reranker-v2-m3    │
                              └────────────┬──────────────┘
                                           │
                              ┌────────────▼──────────────┐
                              │ Gate: rerank_score >= 0.5  │
                              └────────────┬──────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  Generation  │ (Gemini)
                                    └─────────────┘
```

---

## 3. Cau truc Project

```
rag_foundation/buoi_08/
├── SPEC_buoi_08.md                  # Dac ta ky thuat
├── README.md                        # File nay
├── requirements.txt                 # Thu vien phu thuoc
├── .env.example                     # Mau cau hinh
├── .gitignore
├── rag.py                           # Semantic baseline (copy tu Buoi 07)
├── advanced_rag.py                  # Advanced RAG pipeline chinh
├── evaluate.py                      # Evaluation benchmark
├── app.py                           # Giao dien Streamlit
├── eval/
│   └── questions.json               # Bo cau hoi benchmark (gold labels)
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   └── chunks_advanced_sample.json
│   ├── test_bm25.py
│   ├── test_semantic_retrieval.py
│   ├── test_hybrid_fusion.py
│   ├── test_reranker.py
│   ├── test_answer_pipeline.py
│   └── test_evaluation_metrics.py
├── reports/                         # Bao cao benchmark (tu dong tao)
└── storage/
    ├── chroma/                      # ChromaDB persistent
    └── huggingface/                 # Cache model reranker
```

---

## 4. Setup

### 4.1 Kich hoat venv (dung chung Buoi 05)
```powershell
# Windows PowerShell
& "..\buoi_05\.venv\Scripts\Activate.ps1"
```

### 4.2 Cai dat thu vien
```bash
pip install -r requirements.txt
```

requirements.txt gom: `rank-bm25`, `chromadb`, `google-genai`, `python-dotenv`,
`transformers`, `torch`, `streamlit`

### 4.3 Cau hinh .env
```bash
cp .env.example .env
# Dien GEMINI_API_KEY vao file .env
```

**Cac bien .env quan trong:**
```
GEMINI_API_KEY=...          # Bat buoc cho Semantic / Generation
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
BM25_TOP_K=20
SEMANTIC_TOP_K=20
RRF_K=60
RRF_BM25_WEIGHT=1.0
RRF_SEMANTIC_WEIGHT=1.0
RERANK_MIN_SCORE=0.50
FINAL_TOP_K=5
```

---

## 5. Canh bao Reranker (quan trong)

- Model `BAAI/bge-reranker-v2-m3` ~1.1GB RAM (FP32 CPU).
- Lan dau chay se tai tu Hugging Face - can Internet.
- Cache tai: `storage/huggingface/`
- Tren CPU, moi batch co the mat 5-30 giay.
- Neu thieu RAM -> giam `RERANK_CANDIDATES` trong .env.
- Khong bat `trust_remote_code=True`.

---

## 6. Cac lenh chinh

### Status (read-only, khong tao resource)
```bash
python advanced_rag.py status --strategy hierarchical
```

### Prepare semantic index (can API key, chi chay khi chu dong)
```bash
python advanced_rag.py prepare-semantic --strategy hierarchical
```

### Truy xuat BM25
```bash
python advanced_rag.py bm25 --strategy hierarchical --question "Dieu 7 quy dinh nhu the nao?"
```

### Truy xuat Hybrid (BM25 + Semantic + RRF)
```bash
python advanced_rag.py hybrid --strategy hierarchical --question "co cau lai thoi han tra no"
```

### Truy xuat Hybrid + Reranking
```bash
python advanced_rag.py hybrid-rerank --strategy hierarchical --question "co cau lai thoi han tra no"
```

### Query (sinh cau tra loi)
```bash
# Mode mac dinh: hybrid_rerank
python advanced_rag.py query --strategy hierarchical --question "Dieu 7 quy dinh nhu the nao?"

# Chon mode khac
python advanced_rag.py query --strategy hierarchical --mode semantic --question "..."
```

### Compare (so sanh 4 mode, khong generation)
```bash
python advanced_rag.py compare --strategy hierarchical --question "Dieu 7 quy dinh nhu the nao?"
```

### Test offline
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Evaluate (can index semantic & API key)
```bash
python evaluate.py --strategy hierarchical --k 5
python evaluate.py --modes bm25 semantic hybrid --k 1 3 5 --save
```

### Streamlit UI
```bash
streamlit run app.py
```

---

## 7. Cac lenh so sanh thu cong (Manual Comparison)

Cac cau hoi goi y de so sanh 4 mode:

**A. Exact legal reference (BM25 manh):**
```
Dieu 7 quy dinh nhu the nao ve co cau lai thoi han tra no?
```

**B. Paraphrase semantic (Semantic manh):**
```
Khach hang gap kho khan co the duoc dieu chinh ky han tra no ra sao?
```

**C. Multi-concept (Hybrid manh):**
```
Phan loai no va trich lap du phong duoc thuc hien nhu the nao?
```

**D. Out-of-scope (tat ca mode phai reject):**
```
Ngan hang nao co lai suat tiet kiem cao nhat hom nay?
```

> **Luu y:** Khong khang dinh truoc mode nao thang. Dung ranking va metrics thuc te.

---

## 8. Giai thich cac chi so

### 8.1 Scores retrieval
| Chi so | Mo ta | Pham vi | Thap = tot? |
|---|---|---|---|
| BM25 score | Diem TF-IDF co trong so (Okapi BM25) | 0 -> +inf | Khong, cao hon = lien quan hon |
| Cosine distance | Khoang cach vector trong Chroma (1 - cosine_sim) | 0.0 -> 2.0 | Co, gan 0 = rat lien quan |
| RRF score | Rank-based fusion: sum(w / (k + rank)) | 0 -> w/k | Khong, cao hon = tot hon |
| Rerank score | Sigmoid cua logit cross-encoder | 0.0 -> 1.0 | Khong, cao hon = lien quan hon |

### 8.2 Candidate K vs Final K
- **Candidate K**: so luong ung vien moi nhanh lay truoc khi fusion/rerank (default 20).
- **Final K**: so luong ket qua cuoi cung tra ve cho nguoi dung (default 5).
- Quy trinh: lay 20 BM25 + 20 Semantic -> fusion -> top 20 fused -> rerank 20 -> tra ve top 5.

---

## 9. Evaluation Metrics

### Cong thuc (binary relevance)
| Metric | Cong thuc | Vi du tinh tay |
|---|---|---|
| Hit@K | 1 neu co relevant doc trong top-K, 0 neu khong | retrieved=[c1,c2], rel={c2}, k=2 -> Hit@2=1.0 |
| Recall@K | hits_in_top_k / total_relevant | hits=1, rel=2 -> Recall=0.5 |
| MRR@K | 1 / rank_of_first_relevant | relevant o rank=2 -> MRR=0.5 |
| nDCG@K | DCG@K / IDCG@K (IDCG la thu tu ly tuong) | DCG=0.631, IDCG=1.631 -> nDCG=0.387 |
| Latency | mean va p50 ms cua tung mode | p50=120ms |

### Gioi han gold labels
- Tat ca cau hoi trong `eval/questions.json` co `needs_human_review=true`.
- Gold labels duoc xay dung tu fixture, chua qua xac nhan chuyen gia.
- **Bao cao Evaluation se co WARNING va khong tuyen bo mode chien thang chinh thuc.**
- De co ket qua chinh thuc: can annotator xac nhan relevant_chunk_ids cho tung query.

---

## 10. Troubleshooting

### Model download that bai
```
# Dat cach thu cong
pip install huggingface_hub
huggingface-cli download BAAI/bge-reranker-v2-m3
# Hoac dat HF_HOME de thay doi cache dir
set HF_HOME=d:\your\cache\dir
```

### CPU cham
- Giam RERANK_CANDIDATES (tu 20 xuong 5).
- Dung mode `hybrid` thay vi `hybrid_rerank`.
- Reranker chi load khi mode `hybrid_rerank` duoc goi.

### Thieu RAM
- Model ~1.1GB, kem Python overhead ~2GB total.
- Dong cac ung dung khac truoc khi chay.
- Hoac chi chay mode `bm25` va `semantic`.

### API key loi / het quota
- Kiem tra GEMINI_API_KEY trong .env.
- Semantic retrieval can API key de sinh query embedding.
- BM25 mode hoat dong hoan toan offline, khong can API key.

### Collection khong ton tai
- Chay `python advanced_rag.py status` truoc.
- Neu collection_exists=False, chay `prepare-semantic` truoc.

### Import loi khi test
- Dam bao dang chay tests tu thu muc buoi_08/ hoac them `sys.path.insert`.
- Cac test file dung `BASE_DIR = Path(__file__).resolve().parent.parent`.

---

## 11. Trang thai Buoi 08

- **Buoc 01**: Kiem tra baseline Buoi 07 (PASS).
- **Buoc 02**: Tao cau truc project, fixture, SPEC (Hoan thanh).
- **Buoc 04**: BM25 tokenizer + corpus + retrieval (Hoan thanh).
- **Buoc 05**: Semantic candidate stage + status (Hoan thanh).
- **Buoc 06**: RRF fusion + hybrid retrieval (Hoan thanh).
- **Buoc 07**: Cross-encoder reranker lazy-load (Hoan thanh).
- **Buoc 08**: Answer pipeline + CLI query/compare (Hoan thanh).
- **Buoc 09**: Streamlit UI 4 tab (Hoan thanh).
- **Buoc 10**: Test day du (47 tests PASS), evaluator, README (Hoan thanh).

---

*Khong phai tu van phap ly. Ket qua RAG chi de nghien cuu ky thuat.*
