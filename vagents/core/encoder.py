class TextEncoder:
    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Please install sentence-transformers to use TextEncoder."
            )
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()
