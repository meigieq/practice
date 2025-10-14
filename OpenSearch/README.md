## OpenSearch


### 디렉토리 구조
```
OpenSearch/
├── indexing.py            # 인덱싱 API (문서 -> OpenSearch)
├── server.py              # QA/RAG API (질의 -> 검색 -> LLM)
├── index_create/          # 인덱스 생성/매핑/설정
├── prompts/               # LLM 프롬프트 템플릿
├── search/                # 하이브리드 검색 모듈
├── utils/                 # OpenSearch, 임베딩, 청킹 등 유틸
├── .env                   # 환경변수 파일
└── requirements.txt       # 패키지 목록
```
### 실행 방법

1. 패키지 설치
    pip install -r requirements.txt

2. 실행

    indexing.py
    - uvicorn indexing:app --host 0.0.0.0 --port 8001
    - /indexing 엔드포인트에 파싱된 문서 폴더 경로 입력 -> OpenSearch 인덱싱

    server.py
    - uvicorn server:app --host 0.0.0.0 --port 8002
    - /rag/sse 엔드포인트에 question 입력, top_k는 기본값 5로 설정됨

### 참고 사항

    아래 AWS 인스턴스 실행 후 시작 필요
    - LLM_Server (15.165.181.171)
        > docker start qwen3-embedding
        > docker start qwen3-32b
    - OS_Server (43.202.20.141)
        > cd opensearch
        > sudo docker compose start










