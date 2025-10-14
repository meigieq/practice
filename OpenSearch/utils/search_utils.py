from typing import List, Dict, Any, Mapping

# -- metadata --
def md_get(x: Any) -> Dict:
    if isinstance(x, Mapping):
        return x.get("metadata") or {}
    meta = getattr(x, "metadata", {}) or {}
    return meta.get("metadata") or {}

def content_fallback(x: Any) -> str:
    md_meta = md_get(x)
    body = (md_meta.get("md_content") or "").strip()
    if not body:
        meta = getattr(x, "metadata", {}) if not isinstance(x, Mapping) else x
        body = (meta.get("md_content") or "").strip()
    return body

# -- LLM Context --
def join_context(blocks: List[Dict]) -> str:
    lines = []
    for i, r in enumerate(blocks, 1):
        title = (r.get("doc_title") or "").strip() or f"Doc{i}"
        body  = (r.get("content") or "").strip()
        if not body:
            continue
        lines.append(f"[{i}: {title}]\n{body}")
    return "\n\n".join(lines)

# -- 검색 결과 정규화 --
def normalize_results(results_tuples) -> List[Dict]:
    results = []
    for doc, score in results_tuples:
        meta    = doc.metadata or {}
        md_meta = meta.get("metadata") or {}

        doc_id    = (meta.get("doc_id") or md_meta.get("doc_id")) or ""
        doc_title = (meta.get("doc_title") or md_meta.get("doc_title") or "").strip()
        content = content_fallback(doc)

        results.append({
            "doc_id": doc_id,
            "doc_title": doc_title,
            "hybrid_score": float(score),
            "content": content,
            "_id": meta.get("_id"),
        })
    return results

# -- 문서별 그룹핑 --
def group_by_doc(results: List[Dict], max_docs: int = 3, keep_chunks_per_doc: int = 3) -> List[Dict]:
    buckets: Dict[str, List[Dict]] = {}
    for r in results:
        did = r.get("doc_id") or r.get("doc_title")
        buckets.setdefault(did, []).append(r)

    grouped = []
    for did, items in buckets.items():
        items.sort(key=lambda x: x.get("hybrid_score", 0.0), reverse=True)
        top = items[0]
        keep = items[:keep_chunks_per_doc]

        grouped.append({
            "doc_id": did,
            "doc_title": top.get("doc_title") or "",
            "best_score": float(top.get("hybrid_score", 0.0)),
            "chunks": [
                {
                    "score": float(x.get("hybrid_score", 0.0)),
                    "content": (x.get("content") or ""),
                }
                for x in keep
            ],
        })

    grouped.sort(key=lambda g: g["best_score"], reverse=True)
    return grouped[:max_docs]