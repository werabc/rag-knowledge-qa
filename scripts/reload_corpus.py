"""
重建在线语料：删光文档后用 test_data 4 个 txt + 扫描件 PDF 重新上传（分块策略变更后必须重传才生效）。
用法：python -X utf8 scripts/reload_corpus.py
"""
import os
import sys

import requests

BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCAN = os.path.join(ROOT, "data", "scan_xuanhe.pdf")

files = [os.path.join(ROOT, "test_data", n) for n in
         ("kb_sample.txt", "decoy_zh.txt", "roadmap_zh.txt", "star_editor.txt")]
if os.path.exists(SCAN):
    files.append(SCAN)
else:
    print(f"⚠ 缺少 {SCAN}，先跑 python -X utf8 scripts/make_scan_pdf.py")
    sys.exit(1)

r = requests.get(f"{BASE}/api/v1/documents", params={"page": 1, "size": 100},
                 timeout=30).json()
for item in r.get("items", r if isinstance(r, list) else []):
    doc_id = item["id"] if isinstance(item, dict) else item
    requests.delete(f"{BASE}/api/v1/documents/{doc_id}", timeout=30)
    print(f"删除 {item.get('filename', doc_id) if isinstance(item, dict) else doc_id}")

for path in files:
    with open(path, "rb") as f:
        r = requests.post(f"{BASE}/api/v1/documents/upload",
                          files={"file": (os.path.basename(path), f)}, timeout=300)
    r.raise_for_status()
    d = r.json()
    print(f"上传 {d['filename']} → {d['chunk_count']} 块 (status={d['status']})")

r = requests.get(f"{BASE}/api/v1/documents", params={"page": 1, "size": 100},
                 timeout=30).json()
items = r.get("items", r if isinstance(r, list) else [])
print(f"完成：现库 {len(items)} 个文档")
