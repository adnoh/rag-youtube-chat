"""
Tests for backend.rag.retriever — threshold-filter logic and cosine similarity helpers.

Run with:
    cd app && python -m pytest tests/rag/test_retriever.py -v
"""
from __future__ import annotations

import math
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from backend.rag.retriever import _cosine_similarity_batch, retrieve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str, video_id: str, embedding: list[float]) -> dict:
    return {
        "id": chunk_id,
        "video_id": video_id,
        "content": f"content for {chunk_id}",
        "embedding": embedding,
    }


def _make_video(video_id: str, title: str) -> dict:
    return {"id": video_id, "title": title}


# ---------------------------------------------------------------------------
# retrieve() — min_score threshold filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRetrieveMinScore:

    async def test_all_chunks_above_threshold_returned(self):
        """Chunks with score >= min_score are all included."""
        query = [1.0, 0.0]
        chunks = [
            _make_chunk("c1", "v1", [1.0, 0.0]),   # score = 1.0
            _make_chunk("c2", "v1", [0.9, 0.1]),   # score ≈ 0.994
        ]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
        ):
            results = await retrieve(query, k=5, min_score=0.5)
        assert len(results) == 2

    async def test_all_chunks_below_threshold_returns_empty(self):
        """When no chunks meet min_score, returns []."""
        query = [1.0, 0.0]
        chunks = [
            _make_chunk("c1", "v1", [0.0, 1.0]),   # score = 0.0 (orthogonal)
            _make_chunk("c2", "v1", [-1.0, 0.0]),  # score = -1.0 (opposite)
        ]
        with patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)):
            results = await retrieve(query, k=5, min_score=0.5)
        assert results == []

    async def test_mixed_scores_only_above_threshold_included(self):
        """Only chunks with score >= min_score appear in results."""
        query = [1.0, 0.0]
        chunks = [
            _make_chunk("c_high", "v1", [1.0, 0.0]),   # score = 1.0
            _make_chunk("c_low", "v1", [0.0, 1.0]),    # score = 0.0
        ]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
        ):
            results = await retrieve(query, k=5, min_score=0.5)
        assert len(results) == 1
        assert results[0]["chunk_id"] == "c_high"

    async def test_score_exactly_at_threshold_is_included(self):
        """Boundary: score == min_score is kept because filter uses strict `<`."""
        # cos(60 degrees) = 0.5; unit vector at 60 degrees from [1,0]
        query = [1.0, 0.0]
        half_score_embedding = [0.5, math.sqrt(3) / 2]  # unit vector at 60 degrees
        chunks = [_make_chunk("c_boundary", "v1", half_score_embedding)]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
        ):
            results = await retrieve(query, k=5, min_score=0.5)
        # Score should be ≈ 0.5, which is NOT < 0.5, so chunk is included
        assert len(results) == 1
        assert pytest.approx(results[0]["score"], abs=1e-4) == 0.5

    async def test_empty_db_returns_empty(self):
        """When DB has no chunks, returns [] immediately."""
        with patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=[])):
            results = await retrieve([1.0, 0.0], k=5, min_score=0.5)
        assert results == []

    async def test_zero_min_score_returns_all_up_to_k(self):
        """min_score=0.0 acts as no filter — all non-negative-score chunks up to k returned."""
        query = [1.0, 0.0]
        # Use orthogonal embeddings: score = 0.0, which equals min_score exactly (kept)
        chunks = [_make_chunk(f"c{i}", "v1", [0.0, 1.0]) for i in range(3)]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
        ):
            results = await retrieve(query, k=5, min_score=0.0)
        assert len(results) == 3

    async def test_none_min_score_uses_config_default(self):
        """When min_score is None, config.RETRIEVAL_MIN_SCORE is used as default."""
        query = [1.0, 0.0]
        chunks = [
            _make_chunk("c_above", "v1", [1.0, 0.0]),  # score = 1.0 — above any sane default
        ]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
            patch("backend.config.RETRIEVAL_MIN_SCORE", 0.3),
        ):
            results = await retrieve(query, k=5, min_score=None)
        assert len(results) == 1

    async def test_invalid_min_score_above_1_raises(self):
        """min_score > 1.0 raises ValueError (invalid cosine range)."""
        with pytest.raises(ValueError, match="min_score"):
            await retrieve([1.0, 0.0], k=5, min_score=1.5)

    async def test_invalid_min_score_below_neg1_raises(self):
        """min_score < -1.0 raises ValueError (invalid cosine range)."""
        with pytest.raises(ValueError, match="min_score"):
            await retrieve([1.0, 0.0], k=5, min_score=-1.1)

    async def test_results_sorted_descending(self):
        """Results are returned in descending score order."""
        query = [1.0, 0.0]
        chunks = [
            _make_chunk("c_low", "v1", [0.7, 0.3]),   # lower cosine sim
            _make_chunk("c_high", "v1", [1.0, 0.0]),  # higher cosine sim
        ]
        with (
            patch("backend.rag.retriever.repository.list_chunks", new=AsyncMock(return_value=chunks)),
            patch(
                "backend.rag.retriever.repository.get_video",
                new=AsyncMock(return_value=_make_video("v1", "Test Video")),
            ),
        ):
            results = await retrieve(query, k=5, min_score=0.0)
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]


# ---------------------------------------------------------------------------
# _cosine_similarity_batch — zero-norm edge cases
# ---------------------------------------------------------------------------

class TestCosineSimilarityBatch:

    def test_normal_similarity(self):
        """Identical vectors have similarity 1.0."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        assert result[0] == pytest.approx(1.0)

    def test_orthogonal_vectors_similarity_zero(self):
        """Orthogonal vectors have similarity 0.0."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[0.0, 1.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        assert result[0] == pytest.approx(0.0)

    def test_opposite_vectors_similarity_negative_one(self):
        """Opposite vectors have similarity -1.0."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[-1.0, 0.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        assert result[0] == pytest.approx(-1.0)

    def test_zero_query_vector_returns_zeros(self):
        """Zero-norm query vector returns all-zero similarities (no div by zero)."""
        query = np.array([0.0, 0.0], dtype=np.float32)
        matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        np.testing.assert_array_equal(result, [0.0, 0.0])

    def test_zero_matrix_row_does_not_crash_or_produce_nan(self):
        """A zero-norm row in matrix does not produce NaN (clamped to 0 similarity)."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        assert not np.any(np.isnan(result))
        assert result[1] == pytest.approx(1.0)

    def test_returns_float32_array(self):
        """Output dtype is float32."""
        query = np.array([1.0, 0.0], dtype=np.float32)
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _cosine_similarity_batch(query, matrix)
        assert result.dtype == np.float32
