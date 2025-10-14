import os, json, yaml
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Query
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from search.hybrid_search import hybrid_search
from utils.opensearch_client import get_client
from utils.qwen_utils import process_qwen_chunk 
from utils.qwen_embedding import OllamaEmbeddingClient
from utils.search_utils import join_context, normalize_results, group_by_doc

load_dotenv()

app = FastAPI()

# -- Config --
KEYWORD_INDEX = os.getenv("KEYWORD_INDEX")
VECTOR_INDEX  = os.getenv("VECTOR_INDEX")
VECTOR_FIELD = os.getenv("VECTOR_FIELD")
EMBED_MODEL = os.getenv("EMBED_MODEL")
EMBED_URL = os.getenv("EMBED_URL")
PROMPT_FILE = Path(__file__).parent / "prompts" / "prompt.yaml"

# -- LLM --
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_URL = os.getenv("OLLAMA_URL")

# -- 변수 --
client = get_client()
embedder = OllamaEmbeddingClient(EMBED_URL, EMBED_MODEL)

# -- LLM 설정 --
def make_llm(temperature: float = 0.7):
    kw = {"model": OLLAMA_MODEL, "base_url": OLLAMA_URL, "temperature": temperature}
    return ChatOllama(**kw)

# -- 프롬프트 설정 --
def load_prompts() -> dict:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_prompt():
    prompts = load_prompts()
    return ChatPromptTemplate.from_messages([
        ("system", prompts["system"]),
        ("human", prompts["human"]),
    ])

# -- 데이터 전송 값 --
def sse(event: str, data) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")

# -- app --
@app.get("/info")
def info():
    return {"ok": True, "model": OLLAMA_MODEL}

@app.get("/rag/sse")
def rag_sse(question: str = Query(...), top_k: int = Query(5, ge=1, le=20)):
    results_tuples = hybrid_search(
        question=question,
        keyword_index_name=KEYWORD_INDEX,
        vector_index_name=VECTOR_INDEX,
        embed_fn=embedder.embed,
        client=client,
        top_k=top_k,
        vector_field=VECTOR_FIELD,
    )
    results = normalize_results(results_tuples)

    prompt = build_prompt()
    llm = make_llm()
    parser = StrOutputParser()
    context_text = join_context(results)
    chain = ({"question": RunnablePassthrough(), "context": lambda _: context_text}
             | prompt | llm | parser)

    final_text = chain.invoke(question)

    # 추론 내용 분리
    inside_think = {"v": False}
    reasoning_buf, answer_buf = [], []
    for kind, text in process_qwen_chunk(final_text, inside_think):
        if not text:
            continue
        if kind == "reason":
            reasoning_buf.append(text)
        else:
            answer_buf.append(text)

    answer = ("".join(answer_buf).strip()) or final_text.strip()
    # reasoning_full = "".join(reasoning_buf).strip() # 추론 내용 필요 시 주석 제거

    # 출처
    grouped_docs = group_by_doc(results, max_docs=5, keep_chunks_per_doc=3)
    sources = []
    for rank, g in enumerate(grouped_docs, start=1):
        chunks = [
            ch for ch in (g.get("chunks") or [])
            if (ch.get("content") or (ch.get("metadata") or {}).get("md_content") or "").strip()
        ]
        if not chunks:
            continue

        out = {
            "rank": rank,
            "title": (g.get("doc_title") or "").strip(),
            "score": round(float(g.get("best_score", 0.0)), 3),
            "content": (chunks[0].get("content") or (chunks[0].get("metadata") or {}).get("md_content") or ""),
            "chunks": [{**ch, "content": (ch.get("content") or (ch.get("metadata") or {}).get("md_content") or "")} for ch in chunks],
        }
        sources.append(out)

    return {
        "ok": True,
        "answer": answer,
        # "reasoning_full": reasoning_full, # 추론 내용 필요 시 주석 제거
        "sources": sources,
    }