import re, base64, mimetypes
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, List, Dict, Tuple, Iterable

# -- 정규식 패턴 --
MD_SYM = re.compile(r'[@#*`]+')
IMG_MD = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<path><[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)')
IMAGE_EXT = {"jpg","jpeg","png","gif","bmp","tif","tiff","svg","webp"}
DOC_MAP = {"pdf": "pdf", "md": "md", "ppt": "ppt", "docx": "docx", "doc": "doc", "xlsx": "xlsx", "xls": "xls"}
PAGE_MARK = re.compile(r'^\s*\{\s*(\d+)\s*\}\s*[-—–_=*~\s]{3,}\s*$', re.MULTILINE)
PAGE_INDEX_PATTERNS = [
    re.compile(r'(?:^|[_-])page[_-]?(\d+)[^0-9]+(?:figure|picture|img|image|fig)?[_-]?(\d+)', re.I),
    re.compile(r'(?:^|[_-])p(?:age)?[_-]?(\d+)[^0-9]+(\d+)', re.I),
    re.compile(r'(?:^|[_-])page[_-]?(\d+)[_-](\d+)', re.I),
]

# -- 함수 --
def strip_md(md: str) -> str:
    s = IMG_MD.sub('', md or '')
    s = MD_SYM.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# base64, mime
def normalize_data_uri(s):
    if s is None:
        return None, None
    
    if isinstance(s, (bytes, bytearray)):
        try:
            st = s.decode("utf-8")
            if st.startswith("data:") and ";base64," in st:
                header, b64 = st.split(";base64,", 1)
                return b64, (header[5:] or None)
        except UnicodeDecodeError:
            pass
        return base64.b64encode(s).decode("ascii"), None

    st = str(s).strip()

    if st.startswith("data:") and ";base64," in st:
        header, b64 = st.split(";base64,", 1)
        return b64, (header[5:] or None)
    if len(st) % 4 == 0 and re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", st or ""):
        return st, None
    return None, None

# 바이트를 base64 문자열로 변환
def bytes_to_b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

# 파일을 읽어 (base64, mime)로 반환
def file_to_b64(p: str | Path):
    p = Path(p)
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return bytes_to_b64(p.read_bytes()), mime

# 파일 URL/경로에서 문서 타입 추출
def doc_type_url(file_url: str | None) -> str:
    if not file_url:
        return "unknown"
    path = urlparse(str(file_url)).path
    ext = Path(path).suffix.lower().lstrip(".")
    if not ext:
        return "unknown"
    if ext in IMAGE_EXT:
        return "image"
    if ext in DOC_MAP:
        return DOC_MAP[ext]
    mt, _ = mimetypes.guess_type(path)
    if mt and mt.startswith("image/"):
        return "image"
    return ext

# {n}-----와 같은 페이지 기준으로 문서를 분리
def split_page(md: str):
    matches = list(PAGE_MARK.finditer(md or ""))
    if not matches:
        return [(1, (md or "").strip())]

    pages = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        page_text = md[start:end].strip()
        page_number = int(m.group(1)) + 1 # 페이지 번호가 0으로 시작함
        pages.append((page_number, page_text))
    return pages

# 파일명에서 페이지, 인덱스 번호 추정
def parse_page_idx(filename: str):
    stem = Path(filename).stem
    for pat in PAGE_INDEX_PATTERNS:
        m = pat.search(stem)
        if m: return int(m.group(1)), int(m.group(2))
    nums = [int(x) for x in re.findall(r'\d+', stem)]
    if len(nums) >= 2: return nums[0], nums[1]
    if len(nums) == 1: return nums[0], None
    return None, None

# 파일명과 정확히 일치하는 경로 선택
def pick_rel_by_basename(rel_candidates: list[str] | None, want_name: str) -> str | None:
    want = Path(want_name).name.lower()
    for rel in rel_candidates or []:
        if Path(rel).name.lower() == want:
            return rel
    return None

def extract_raw_path(path_token: str) -> str:
    raw = (path_token or "").strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()
    return raw.split()[0] if " " in raw else raw

def resolve_relpath(raw: str, all_image_relpaths: Optional[Iterable[str]]) -> str:
    parts = raw.replace("\\", "/").split("/")
    basename = Path(parts[-1]).name
    if all_image_relpaths:
        picked = pick_rel_by_basename(all_image_relpaths, basename)
        if picked:
            return picked
    if "images" in parts:
        i = parts.index("images")
        return "/".join(parts[i:])
    return f"images/{basename}"

def b64_from_source(
    raw: str,
    base_dir: Path,
    relpath: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:

    lower = raw.lower()
    if lower.startswith("data:"):
        b64, mime = normalize_data_uri(raw)
        return (b64, mime)
    if lower.startswith("http://") or lower.startswith("https://"):
        return (None, None)
    if relpath:
        p = (base_dir / relpath)
        if p.exists():
            return file_to_b64(p)
    return (None, None)

# 마크다운 내 이미지 태그를 모두 추출하여 리스트 반환
def image_refs_get(
    md_text: str,
    doc_id: str,
    all_image_relpaths: Optional[Iterable[str]] = None,
    base_dir: Optional[str | Path] = None,
) -> List[Dict]:

    base_dir = Path(base_dir or ".")
    out: List[Dict] = []

    for m in IMG_MD.finditer(md_text or ""):
        raw_token = extract_raw_path(m.group("path"))
        relpath = resolve_relpath(raw_token, all_image_relpaths)
        imgname = Path(relpath).name
        page, index = parse_page_idx(imgname)

        # base64 인코딩
        thumb_b64, thumb_mime = b64_from_source(raw_token, base_dir, relpath)

        out.append({
            "url": f"/files/{doc_id}/{relpath}",
            "local_name": imgname,
            "relpath": relpath,
            "page": page,
            "index": index,
            "thumb_b64": thumb_b64, 
            "thumb_mime": thumb_mime,
        })

    return out