"""
Embedding Service – lazy-loads a sentence-transformer model and provides
batch encoding for topic tagging and chunk deduplication.

The model is stored locally in ``models/bge-small-en/`` so it ships with the
project instead of relying on the default HuggingFace cache.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import numpy as np

from app.config import EMBEDDING_MODEL

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Local path: <backend>/models/bge-small-en/
_LOCAL_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bge-small-en"
)

_model: "SentenceTransformer | None" = None


def get_model() -> "SentenceTransformer":
    """Lazy-load and cache the embedding model (singleton).

    If the model exists locally in ``models/bge-small-en/`` it is loaded
    from disk.  Otherwise it is downloaded from HuggingFace and saved to
    that directory for future use.
    """
    global _model
    if _model is not None:
        return _model

    from sentence_transformers import SentenceTransformer

    if os.path.isdir(_LOCAL_MODEL_DIR) and os.listdir(_LOCAL_MODEL_DIR):
        logger.info("Loading embedding model from local path: %s", _LOCAL_MODEL_DIR)
        _model = SentenceTransformer(_LOCAL_MODEL_DIR)
    else:
        logger.info(
            "Downloading embedding model '%s' → %s …", EMBEDDING_MODEL, _LOCAL_MODEL_DIR
        )
        _model = SentenceTransformer(EMBEDDING_MODEL)
        _model.save(_LOCAL_MODEL_DIR)
        logger.info("Model saved to %s", _LOCAL_MODEL_DIR)

    logger.info("Embedding model loaded successfully.")
    return _model


def download_model() -> str:
    """Pre-download the model into the local directory. Returns the path."""
    get_model()  # triggers download + save
    return _LOCAL_MODEL_DIR


def encode(texts: list[str], batch_size: int = 16) -> np.ndarray:
    """Encode a list of texts into embedding vectors.

    Args:
        texts: strings to encode.
        batch_size: batch size for inference (keep small for CPU).

    Returns:
        A 2-D numpy array of shape ``(len(texts), embedding_dim)``.
    """
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings)
