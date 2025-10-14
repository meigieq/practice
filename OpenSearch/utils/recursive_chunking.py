import re
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
 
# 정규식 패턴
TABLE = re.compile(r"(?:^[^\r\n]*\|[^\r\n]*\|[^\r\n]*(?:\r?\n|$)){1,}", re.MULTILINE)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
PATTERN = re.compile(f"{TABLE.pattern}|{IMAGE.pattern}", re.MULTILINE)
CAPTION = re.compile(
    r"""
        ^\s{0,4}
        (?:\#{1,6}\s*)?
        (?:\*\*)?
        (?:figure|fig\.?|table|tbl\.?|그림|표)
        (?:\s+[0-9][\w\-\.\)]*)?
        \s*[:：#\-–—]?\s*
        .*?
        (?:\*\*)?\s*$
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE
)
BLANK = re.compile(r"^\s*$")
IGNORABLE = re.compile(r"(?i)\s*(?:<span[^>]*>.*?</span>|<span[^>]*>|</span>|<br\s*/?>)\s*")

# 최소 길이 설정
def limit_select(s: str, min_chars=20) -> bool:
    return len(s) >= min_chars and bool(re.search(r'\w', s))

# 표, 이미지 구분
def split_blocks(text: str):
    segs, last = [], 0

    for m in PATTERN.finditer(text or ""):
        before = text[last:m.start()]
        before_lines = before.splitlines()
        cap_above = None

        k = len(before_lines) - 1
        while k >= 0 and (IGNORABLE.match(before_lines[k]) or BLANK.match(before_lines[k])):
            k -= 1
        if k >= 0 and CAPTION.match(before_lines[k]):
            cap_above = before_lines[k]
            before = "\n".join(before_lines[:k]).rstrip()

        if before:
            segs.append(("text", before))

        block = m.group(0)
        
        after_all = text[m.end():]
        after_lines = after_all.splitlines(keepends=True)
        cap_below = None
        j = 0
        while j < len(after_lines) and (IGNORABLE.match(after_lines[j]) or BLANK.match(after_lines[j])):
            j += 1
        if j < len(after_lines) and CAPTION.match(after_lines[j]):
            cap_below = after_lines[j].rstrip("\r\n")
            j += 1

        after_consumed_text = "".join(after_lines[:j])
        atomic = "\n".join([x for x in [cap_above, block, cap_below] if x]).strip()
        segs.append(("atomic", atomic))
        last = m.end() + len(after_consumed_text)

    tail = text[last:]
    if tail:
        segs.append(("text", tail))

    return segs

# 헤더 기준 분할
def build_splitter(chunk_size=1200, chunk_overlap=100):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[r"(?:^|\n)\s*#{1,4}\s+"],
        is_separator_regex=True,
    )

# 청크 구성
def chunk_text(text: str, splitter, limit: int = 1200) -> List[str]:
    segs = split_blocks(text)
    out = []
    i = 0
    n = len(segs)

    while i < n:
        kind, piece = segs[i]
        piece = (piece or "").strip()
        if not piece:
            i += 1
            continue

        if kind == "atomic":
            attached = False
            if out and out[-1][0] == "text" and len(out[-1][1]) + 2 + len(piece) <= limit:
                out[-1] = ("text", out[-1][1].rstrip() + "\n\n" + piece)
                attached = True
            elif i + 1 < n and segs[i + 1][0] == "text":
                nxt = (segs[i + 1][1] or "").strip()
                if nxt and len(piece) + 2 + len(nxt) <= limit:
                    segs[i + 1] = ("text", piece + "\n\n" + nxt)
                    attached = True
            if not attached:
                out.append(("atomic", piece))
            i += 1
            continue

        out.append(("text", piece))
        i += 1

    final_chunks = []
    for kind, block in out:
        if kind == "atomic":
            if limit_select(block):
                final_chunks.append(block)
        else:
            for ch in splitter.split_text(block):
                ch = ch.strip()
                if limit_select(ch):
                    final_chunks.append(ch)

    return final_chunks
