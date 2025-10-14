import os
from collections import defaultdict
from utils.opensearch_client import get_client
from .index_field_utils import strip_md
from .create_index import create_keyword_index, create_vector_index
from .keyword_indexing import keyword_create_and_index
from .vector_indexing import vector_create_and_index

client = get_client()

KEYWORD_INDEX = os.getenv("KEYWORD_INDEX_NAME", "keyword_documents")
VECTOR_INDEX  = os.getenv("VECTOR_INDEX_NAME",  "vector_documents")
ONLY = {x for x in os.getenv("INDEX_ONLY_DOC_IDS", "").split(",") if x}

def preprocess_docs(docs):
    processed = []
    for d in docs:
        md_raw = d.page_content or ""
        meta = dict(d.metadata or {})
        meta["md_content"] = md_raw
        d.page_content = strip_md(md_raw)
        d.metadata = meta
        processed.append(d)
    return processed

def ensure_indices(_client, keyword_index=KEYWORD_INDEX, vector_index=VECTOR_INDEX):
    keyword_config = create_keyword_index()
    if not _client.indices.exists(index=keyword_index):
        _client.indices.create(index=keyword_index, body=keyword_config)

    vector_config = create_vector_index()
    if not _client.indices.exists(index=vector_index):
        _client.indices.create(index=vector_index, body=vector_config)

def index_docs(docs, keyword_index=KEYWORD_INDEX, vector_index=VECTOR_INDEX):
    _client = client
    docs = preprocess_docs(docs)
    ensure_indices(_client, keyword_index, vector_index)

    groups = defaultdict(list)
    for d in docs:
        groups[d.metadata["doc_id"]].append(d)

    results = {"total_docs": len(groups), "per_doc": []}
    for doc_id, group in groups.items():
        doc_title = group[0].metadata.get("doc_title", doc_id)
        print(f"[INDEXING START] - {doc_title}")
        kw = keyword_create_and_index(_client, keyword_index, group)
        print(f"키워드 청크: {kw}")
        vc = vector_create_and_index(_client, vector_index, group)
        print(f"벡터 청크: {vc}")
        print(f"[INDEXING FINISH] - {doc_title}")
        results["per_doc"].append({
            "doc_id": doc_id,
            "doc_title": doc_title,
            "kw_chunks": kw,
            "vec_chunks": vc
        })
    return results