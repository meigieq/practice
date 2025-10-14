from typing import List, Union
from ollama import Client

class OllamaEmbeddingClient:
    def __init__(self, host: str, model: str, timeout: float = 30.0):
        self.client = Client(host=host.rstrip("/"))
        self.model = model
        self.timeout = timeout

    def embed(self, text_or_list: Union[str, List[str]]):
        res = self.client.embed(model=self.model, input=text_or_list)
        
        embs = getattr(res, "embeddings", None)
        if embs is None and isinstance(res, dict):
            embs = res.get("embeddings")

        if embs is None:
            single = getattr(res, "embedding", None)
            if single is None and isinstance(res, dict):
                single = res.get("embedding")
            if single is not None:
                return [float(x) for x in single]
            return None

        if isinstance(text_or_list, str):
            return [float(x) for x in embs[0]]

        return [[float(x) for x in v] for v in embs]
