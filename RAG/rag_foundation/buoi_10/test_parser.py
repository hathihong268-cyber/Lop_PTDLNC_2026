import os
import sys
import re
import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data_dir = Path(__file__).resolve().parent / "graph_rag_labs" / "kb+hops"
df_meta = pd.read_csv(data_dir / "metadata.csv")
df_content = pd.read_csv(data_dir / "content.csv")

def table_to_markdown(table_tag):
    rows = []
    for tr in table_tag.find_all('tr'):
        cells = [re.sub(r'\s+', ' ', td.get_text(separator=" ", strip=True)) for td in tr.find_all(['td', 'th'])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    # Ensure uniform column count
    max_cols = max(len(r) for r in rows)
    formatted_rows = []
    for r in rows:
        r_padded = r + [''] * (max_cols - len(r))
        formatted_rows.append('| ' + ' | '.join(r_padded) + ' |')
    if len(rows) > 1:
        separator = '| ' + ' | '.join(['---'] * max_cols) + ' |'
        formatted_rows.insert(1, separator)
    return '\n'.join(formatted_rows)

print("Testing parser logic on doc 44209...")
sample_html = df_content.iloc[0]['content_html']
soup = BeautifulSoup(sample_html, 'html.parser')
body = soup.body if soup.body else soup

# Check tables in doc 44209
tables = body.find_all('table')
print(f"Total tables: {len(tables)}")
for i, tbl in enumerate(tables[:3]):
    print(f"\n--- Table {i+1} ---")
    print(table_to_markdown(tbl)[:300])

