"""
Similarity utilities – thin wrapper around sklearn cosine similarity.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as _sklearn_cosine


def cosine_similarity_matrix(
    embeddings_a: np.ndarray, embeddings_b: np.ndarray
) -> np.ndarray:
    """Compute pairwise cosine similarity between two sets of embeddings.

    Args:
        embeddings_a: shape ``(N, D)``
        embeddings_b: shape ``(M, D)``

    Returns:
        Similarity matrix of shape ``(N, M)`` with values in ``[-1, 1]``.
    """
    return _sklearn_cosine(embeddings_a, embeddings_b)


def top_k_indices(
    similarities: np.ndarray, k: int = 5, threshold: float = 0.0
) -> list[int]:
    """Return indices of the top-k scores above a threshold from a 1-D array."""
    indices = np.argsort(similarities)[::-1]
    result = []
    for idx in indices:
        if similarities[idx] < threshold:
            break
        result.append(int(idx))
        if len(result) >= k:
            break
    return result
