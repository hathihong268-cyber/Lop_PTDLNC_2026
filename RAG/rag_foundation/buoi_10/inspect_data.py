import os
import sys
import re
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
df_meta = pd.read_csv(data_dir / "metadata.csv")
df_content = pd.read_csv(data_dir / "content.csv")

print(f"Meta shape: {df_meta.shape}")
print(f"Content shape: {df_content.shape}")
print(f"Total documents: {len(df_meta)}")

for idx, row in df_content.head(3).iterrows():
    doc_id = row['id']
    meta_row = df_meta[df_meta['id'].astype(str) == str(doc_id)]
    title = meta_row['title'].values[0] if not meta_row.empty else "N/A"
    
    html = row['content_html']
    soup = BeautifulSoup(html, 'html.parser')
    
    print(f"\n==========================================")
    print(f"Document [{doc_id}]: {title[:80]}...")
    print(f"==========================================")
    
    # Check top-level structures (Chương, Mục, Điều, Khoản...)
    body = soup.body if soup.body else soup
    
    # Let's inspect paragraphs/texts that match Chương, Mục, Điều patterns
    elements = body.find_all(['p', 'table', 'div', 'h1', 'h2', 'h3', 'h4'])
    
    structure_hits = []
    for el in elements:
        text = el.get_text(separator=" ", strip=True)
        if re.match(r'^(CHƯƠNG|Chương)\s+[IVXLCDM\d]+', text, re.IGNORECASE):
            structure_hits.append(('CHUONG', text[:80]))
        elif re.match(r'^(MỤC|Mục)\s+[IVXLCDM\d]+', text, re.IGNORECASE):
            structure_hits.append(('MUC', text[:80]))
        elif re.match(r'^(ĐIỀU|Điều)\s+\d+', text, re.IGNORECASE):
            structure_hits.append(('DIEU', text[:80]))
            
    print(f"Found {len(structure_hits)} structural landmarks:")
    for h_type, h_text in structure_hits[:15]:
        print(f"  [{h_type}] {h_text}")
    if len(structure_hits) > 15:
        print(f"  ... and {len(structure_hits) - 15} more")
