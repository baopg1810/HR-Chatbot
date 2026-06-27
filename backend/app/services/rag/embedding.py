from typing import List

class EmbeddingService:
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Mock embeddings list for compilation
        return [[0.1] * 1536 for _ in texts]
