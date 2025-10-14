from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from pathlib import Path
from index_create.index_utils import index_docs
from utils.doc_load import load_docs

app = FastAPI()

@app.post("/indexing")
def doc_indexing(
    folder_path: str = Query(..., description="파싱된 문서 폴더의 경로")
):
    folder = Path(folder_path)
    if not folder.exists():
        return {"error": f"{folder} 폴더를 찾을 수가 없음"}

    docs = load_docs(folder)

    def event_list():
        res = index_docs(docs)

        for item in res["per_doc"]:
            yield f"[Indexing] - {item['doc_title']}\n"
            yield f"keyword chunks = {item['kw_chunks']}\n"
            yield f"vector chunks = {item['vec_chunks']}\n"

    return StreamingResponse(event_list(), media_type="text/plain")