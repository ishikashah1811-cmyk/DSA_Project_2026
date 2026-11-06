from __future__ import annotations

import os
from typing import Protocol, Sequence

import numpy as np
from numpy.typing import NDArray


class TextEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        ...


class SentenceTransformerEncoder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "CONTENTIQ_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self._model = None

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "Sentence Transformers is required for hashtag recommendations. "
                    "Install backend/requirements.txt."
                ) from error
            self._model = SentenceTransformer(self.model_name)

        vectors = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)
