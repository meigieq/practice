from typing import List, Tuple

def process_qwen_chunk(chunk: str, inside_think: dict) -> List[Tuple[str, str]]:
    """
    Qwen <think> ... </think> 토큰 파서 -> 추론 내용 추출
    """
    out = []
    s = chunk or ""
    while s:
        if s.startswith("<think>"):
            inside_think["v"] = True
            s = s[7:]
            continue
        if s.startswith("</think>"):
            inside_think["v"] = False
            s = s[8:]
            continue

        next_open  = s.find("<think>")
        next_close = s.find("</think>")
        cut_pos = len(s)
        if next_open  != -1: cut_pos = min(cut_pos, next_open)
        if next_close != -1: cut_pos = min(cut_pos, next_close)

        seg, s = s[:cut_pos], s[cut_pos:]
        out.append(("reason" if inside_think["v"] else "answer", seg))
    return out