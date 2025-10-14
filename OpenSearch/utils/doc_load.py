from pathlib import Path
from langchain_core.documents import Document
import re, hashlib

DOC_ID_RE = re.compile(r"-([0-9a-fA-F]{6,64})$")
IMAGE_EXT = {"jpg","jpeg","png","gif"}

def derive_doc_id(pkg_dir: Path) -> str:
    m = DOC_ID_RE.search(pkg_dir.name)
    if m:
        return m.group(1).lower()
    return hashlib.sha256(pkg_dir.name.encode()).hexdigest()[:16]

# 카테고리 구분
def category_select(meta: dict) -> tuple[str, str]:
    title = (meta.get("doc_title") or "").lower()
    url   = (meta.get("file_url") or "").lower()
    name  = f"{title} {url}"

    # 표준
    if any(k in name for k in ["mosar", "ecss", "nasa", "confers", "iso ", "iec ", "ieee ", "omg ", "kasa", "handbook"]):
        return ("std", "SE Standards")

    # 교과서
    elif any(k in name for k in ["textbook", "ebook", "교재", "입문서"]):
        return ("text", "SE Textbooks")

    # 논문
    elif any(k in name for k in ["arxiv", "conference", "journal", "symposium"]):
        return ("paper", "SE Papers")

    else:
        # 기타
        return ("ref", "SE References")

def load_docs(md_root: Path) -> list[Document]:
    docs: list[Document] = []
    for pkg in md_root.iterdir():
        if not pkg.is_dir():
            continue

        doc_id = derive_doc_id(pkg)
        doc_title = pkg.name.replace(f"-{doc_id}", "") if pkg.name.endswith(doc_id) else pkg.name

        for md_file in pkg.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8", errors="ignore")

            md_rel = str(md_file.relative_to(pkg)).replace("\\", "/")

            meta = {
                "doc_id": doc_id,
                "doc_title": doc_title,
                "pkg_dir": str(pkg),
                "md_relpath": md_rel,
                "file_url": f"/files/{doc_id}/{md_rel}",
            }

            cat_id, cat_name = category_select(meta)
            meta["category_id"] = cat_id
            meta["category_name"] = cat_name

            docs.append(Document(page_content=text, metadata=meta))
    return docs
