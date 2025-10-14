from utils.opensearch_client import get_client
from typing import List, Tuple, Dict, Any, Callable, Optional
from collections import defaultdict
from langchain_core.documents import Document

# 키워드 검색
def get_keyword_search(question, client, index_name, top_k):
    keyword_body = {
        "_source": [
            "_id", "doc_id", "doc_title", "content", "file_url",
            "image_refs", "image_thumb", "image_thumb_mime",
            "metadata.*", "metadata.md_content"
        ],
        "query": {
            "multi_match": {
                "query": question,
                "fields": [
                    "content^3",
                    "metadata.md_content^2",
                    "doc_title^2",
                    "metadata.doc_title"
                ],
                "type": "best_fields"
            }
        },
        "size": max(top_k * 3, 30)
    }
    return client.search(index=index_name, body=keyword_body)

# 벡터 검색
def get_vector_search(embed_fn, question, client, index_name, top_k, vector_field):
    vec = embed_fn(question)
    if hasattr(vec, "tolist"):
        vec = vec.tolist()
    vec = [float(x) for x in vec]

    vector_body = {
        "size": int(top_k),
        "_source": { "includes": [
            "_id", "doc_id", "doc_title", "chunk_id",
            "content", "file_url",  "metadata.*"] },
        "query": { "knn": { vector_field: { "vector": vec, "k": max(top_k * 4, 40) } } }
    }
    return client.search(index=index_name, body=vector_body)

# OpenSearch 점수 정규화
def normalize_opensearch_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    hits = resp.get("hits", {}).get("hits", []) or []
    if not hits:
        return resp

    raw_max = resp.get("hits", {}).get("max_score", None)
    if raw_max in (None, 0):
        max_score = max(float(h.get("_score", 0.0)) for h in hits) or 1.0
    else:
        max_score = float(raw_max) or 1.0

    for h in hits:
        s = float(h.get("_score", 0.0))
        h["_score_norm"] = (s / max_score) if max_score != 0 else 0.0

    hits.sort(key=lambda x: x.get("_score_norm", 0.0), reverse=True)
    if hits:
        resp.setdefault("hits", {})
        resp["hits"]["hits"] = hits
        resp["hits"]["max_score"] = float(hits[0].get("_score_norm", 0.0))
    return resp

# OpenSearch -> LangChain Document 변환
def hits_to_docs_with_scores(hits: List[Dict[str, Any]]) -> List[Tuple[Document, float]]:
    out: List[Tuple[Document, float]] = []
    for h in hits:
        src = (h or {}).get("_source", {}) or {}
        content = src.get("content") or (src.get("metadata", {}) or {}).get("md_content") or ""
        meta = dict(src.get("metadata", {}) or {})
        meta.update({
            "_id": h.get("_id"),
            "_index": h.get("_index"),
            "_score_raw": h.get("_score"),
            "_score_norm": h.get("_score_norm"),
            "doc_id": src.get("doc_id") or meta.get("doc_id"),
            "doc_title": src.get("doc_title") or meta.get("doc_title"),
            "file_url":  src.get("file_url")  or meta.get("file_url"),
            "chunk_id":  src.get("chunk_id")  or meta.get("chunk_id"),
        })

        doc = Document(page_content=content, metadata=meta)
        score = float(h.get("_score_norm") if h.get("_score_norm") is not None else (h.get("_score") or 0.0))
        out.append((doc, score))
    return out

# RRF 앙상블
def rrf_ensemble(
    doc_lists: List[List[Tuple[Document, float]]],
    weights: Optional[List[float]] = None,
    k: int = 5,
    c: int = 60, # RRF 상수
    key_fn: Optional[Callable[[Document], Any]] = None
    ) -> List[Tuple[Document, float]]:
    if not doc_lists:
        return []

    n = len(doc_lists)
    if weights is None:
        weights = [1.0 / n] * n
    assert len(weights) == n

    if key_fn is None:
        def key_fn(doc: Document):
            md = doc.metadata or {}
            return (
                md.get("_id") or md.get("doc_id"),
                md.get("chunk_id") or len(doc.page_content or "")
            )

    fused_scores: Dict[Any, float] = defaultdict(float)
    key_to_doc: Dict[Any, Document] = {}

    for w, ranked in zip(weights, doc_lists):
        for rank, (doc, _) in enumerate(ranked, start=1):
            key = key_fn(doc)
            if key not in key_to_doc:
                key_to_doc[key] = doc
            fused_scores[key] += w * (1.0 / (rank + c))
    sorted_items = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

    # 상위 k 반환
    results: List[Tuple[Document, float]] = []
    for key, score in sorted_items[:k]:
        results.append((key_to_doc[key], float(score)))
    return results


# 하이브리드 검색
def hybrid_search(
    question: str,
    keyword_index_name: str,  
    vector_index_name: str,   
    embed_fn: Callable[[str], List[float]],
    client=None,
    top_k: int = 5,
    vector_field: str = "vector_field",
) -> List[Tuple[Document, float]]:

    client = client or get_client()

    # Lexical_Search
    keyword_res = get_keyword_search(question, client, keyword_index_name, top_k)
    kw_res = normalize_opensearch_response(keyword_res)
    kw_docs = hits_to_docs_with_scores(kw_res.get("hits", {}).get("hits", []) or [])

    # Semantic_Search
    vector_res = get_vector_search(embed_fn, question, client, vector_index_name, top_k, vector_field)
    vec_res = normalize_opensearch_response(vector_res)
    vec_docs = hits_to_docs_with_scores(vec_res.get("hits", {}).get("hits", []) or [])

    # RRF
    fused = rrf_ensemble(
        doc_lists=[kw_docs, vec_docs],
        weights=[0.4, 0.6], # 키워드/벡터
        k=top_k,
        c=60,
    )

    # 점수 정규화
    if fused:
        max_score = max(score for _, score in fused)
        if max_score > 0:
            fused = [(doc, score / max_score) for doc, score in fused]

    return fused