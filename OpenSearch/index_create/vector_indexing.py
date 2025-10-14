import os, json
from dotenv import load_dotenv
from opensearchpy import helpers
from utils.doc_load import category_select
from .index_field_utils import strip_md, doc_type_url, split_page, image_refs_get
from utils.qwen_embedding import OllamaEmbeddingClient
from utils.recursive_chunking import build_splitter, chunk_text

load_dotenv()

EMB_MODEL = os.getenv("EMBED_MODEL")
EMB_URL = os.getenv("EMBED_URL")


# -- vector indexing --
def vector_create_and_index(client, index_name, docs):
    splitter = build_splitter(chunk_size=1200, chunk_overlap=100)
    emb = OllamaEmbeddingClient(EMB_URL, EMB_MODEL)

    actions = []
    count = 0
    created_parents = set()

    for d in docs:
        md = dict(d.metadata or {})
        md_all = (md.get("md_content") or d.page_content or "")

        category_id, category_name = category_select(md)

        if category_id not in created_parents:
            actions.append({
                "_op_type": "index",
                "_index": index_name,
                "_id": f"cat::{category_id}",
                "_routing": category_id,
                "_source": {
                    "category_id": category_id,
                    "category_name": category_name,
                    "cat_join": "category"
                }
            })
            created_parents.add(category_id)

        doc_id    = md.get("doc_id")
        doc_title = md.get("doc_title")
        chunk_id    = md.get("chunk_id")

        base_url = (md.get("file_url") or md.get("pdf_relpath") or md.get("md_relpath"))
        if base_url and str(base_url).startswith("/files/"):
            file_url = base_url
        else:
            file_url = f"/files/{doc_id}/{base_url}" if base_url else None
        doc_type = doc_type_url(file_url)

        for page_num, page_text in split_page(md_all):
            parts = chunk_text(page_text, splitter)

            for i, md_chunk in enumerate(parts, 1):
                
                plain_chunk = strip_md(md_chunk)
                if not plain_chunk or len(plain_chunk) < 5:
                    continue

                vector = emb.embed(plain_chunk)

                image_refs = image_refs_get(
                    md_chunk,
                    doc_id,
                    md.get("image_relpaths"),
                    base_dir=md.get("pkg_dir") or ".",
                ) or None
                metadata_image = json.dumps(image_refs, ensure_ascii=False) if image_refs else None
                
                body = {
                    "vector_field": vector,
                    "category_id": category_id,
                    "category_name": category_name,
                    "cat_join": { "name": "doc", "parent": f"cat::{category_id}" },
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "doc_type": doc_type,
                    "page_number": page_num,
                    "chunk_id": chunk_id or i,
                    "content": plain_chunk,
                    "file_url": file_url,
                    "image_refs": image_refs or None,
                    "metadata": {
                        "doc_id": doc_id,
                        "doc_title": doc_title,
                        "doc_type": doc_type,
                        "page_number": page_num,
                        "file_url": file_url,
                        "image": metadata_image,
                        "md_content": md_chunk,
                    }
                }
            
                actions.append({
                    "_op_type": "index",
                    "_index": index_name,
                    "_id": f"{doc_id}::p{page_num}::c{i}",
                    "_routing": category_id,
                    "_source": body
                })
                count += 1

            if actions:
                helpers.bulk(client, actions, refresh=True)
                actions.clear()

    return count
