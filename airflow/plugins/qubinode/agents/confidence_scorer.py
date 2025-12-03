"""
Confidence Scorer for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

Computes confidence scores for task execution based on available
context and knowledge. Used by Manager Agent to decide whether to
execute, escalate, or request approval.

Confidence Score Components:
1. RAG Similarity (40%) - How well RAG results match the query
2. RAG Coverage (30%) - Number of relevant documents found
3. Provider Availability (20%) - Whether an Airflow provider exists
4. Historical Success (10%) - Past troubleshooting success rate

Usage:
    from qubinode.agents import ConfidenceScorer

    scorer = ConfidenceScorer()
    confidence = scorer.compute(
        rag_similarity=0.85,
        rag_hit_count=5,
        provider_exists=True,
        troubleshooting_hits=2
    )
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceWeights:
    """Configurable weights for confidence scoring."""

    rag_similarity: float = 0.40
    rag_coverage: float = 0.30
    provider_availability: float = 0.20
    historical_success: float = 0.10

    def validate(self) -> bool:
        """Validate that weights sum to 1.0."""
        total = (
            self.rag_similarity
            + self.rag_coverage
            + self.provider_availability
            + self.historical_success
        )
        return abs(total - 1.0) < 0.001


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score components."""

    total: float
    rag_similarity_score: float
    rag_coverage_score: float
    provider_score: float
    historical_score: float
    weights: ConfidenceWeights
    raw_inputs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "components": {
                "rag_similarity": {
                    "score": self.rag_similarity_score,
                    "weight": self.weights.rag_similarity,
                    "contribution": self.rag_similarity_score
                    * self.weights.rag_similarity,
                },
                "rag_coverage": {
                    "score": self.rag_coverage_score,
                    "weight": self.weights.rag_coverage,
                    "contribution": self.rag_coverage_score * self.weights.rag_coverage,
                },
                "provider_availability": {
                    "score": self.provider_score,
                    "weight": self.weights.provider_availability,
                    "contribution": self.provider_score
                    * self.weights.provider_availability,
                },
                "historical_success": {
                    "score": self.historical_score,
                    "weight": self.weights.historical_success,
                    "contribution": self.historical_score
                    * self.weights.historical_success,
                },
            },
            "raw_inputs": self.raw_inputs,
        }


class ConfidenceScorer:
    """
    Computes confidence scores for task execution decisions.

    The confidence score determines whether a task should be:
    - Auto-executed (>= 0.8)
    - Executed with logging (0.6 - 0.8)
    - Request approval (0.4 - 0.6)
    - Escalated to Calling LLM (< 0.4)
    """

    # Default thresholds
    THRESHOLD_HIGH = 0.8
    THRESHOLD_MEDIUM = 0.6
    THRESHOLD_LOW = 0.4

    # RAG coverage normalization
    MAX_RAG_HITS = 5  # Normalize hit count to this maximum

    def __init__(self, weights: Optional[ConfidenceWeights] = None):
        """
        Initialize the confidence scorer.

        Args:
            weights: Custom weights for score components
        """
        self.weights = weights or ConfidenceWeights()
        if not self.weights.validate():
            logger.warning("Confidence weights do not sum to 1.0, using defaults")
            self.weights = ConfidenceWeights()

    def compute(
        self,
        rag_similarity: float = 0.0,
        rag_hit_count: int = 0,
        provider_exists: bool = False,
        troubleshooting_hits: int = 0,
        successful_troubleshooting: int = 0,
    ) -> float:
        """
        Compute confidence score for a task.

        Args:
            rag_similarity: Highest similarity score from RAG (0-1)
            rag_hit_count: Number of relevant documents found
            provider_exists: Whether an Airflow provider exists
            troubleshooting_hits: Number of similar past issues found
            successful_troubleshooting: Number with successful resolutions

        Returns:
            Confidence score between 0 and 1
        """
        breakdown = self.compute_with_breakdown(
            rag_similarity=rag_similarity,
            rag_hit_count=rag_hit_count,
            provider_exists=provider_exists,
            troubleshooting_hits=troubleshooting_hits,
            successful_troubleshooting=successful_troubleshooting,
        )
        return breakdown.total

    def compute_with_breakdown(
        self,
        rag_similarity: float = 0.0,
        rag_hit_count: int = 0,
        provider_exists: bool = False,
        troubleshooting_hits: int = 0,
        successful_troubleshooting: int = 0,
    ) -> ConfidenceBreakdown:
        """
        Compute confidence score with detailed breakdown.

        Returns ConfidenceBreakdown with component scores.
        """
        # Normalize inputs
        rag_similarity = max(0.0, min(1.0, rag_similarity))
        rag_hit_count = max(0, rag_hit_count)

        # 1. RAG Similarity Score (0-1)
        rag_similarity_score = rag_similarity

        # 2. RAG Coverage Score (0-1)
        # Normalized: 0 hits = 0, MAX_RAG_HITS+ hits = 1
        rag_coverage_score = min(rag_hit_count / self.MAX_RAG_HITS, 1.0)

        # 3. Provider Score (0 or 1)
        provider_score = 1.0 if provider_exists else 0.0

        # 4. Historical Success Score (0-1)
        # Based on past troubleshooting success rate
        if troubleshooting_hits > 0:
            success_rate = successful_troubleshooting / troubleshooting_hits
            historical_score = min(success_rate, 1.0)
        else:
            # No history means neutral (0.5)
            historical_score = 0.5

        # Compute weighted total
        total = (
            rag_similarity_score * self.weights.rag_similarity
            + rag_coverage_score * self.weights.rag_coverage
            + provider_score * self.weights.provider_availability
            + historical_score * self.weights.historical_success
        )

        return ConfidenceBreakdown(
            total=round(total, 4),
            rag_similarity_score=round(rag_similarity_score, 4),
            rag_coverage_score=round(rag_coverage_score, 4),
            provider_score=provider_score,
            historical_score=round(historical_score, 4),
            weights=self.weights,
            raw_inputs={
                "rag_similarity": rag_similarity,
                "rag_hit_count": rag_hit_count,
                "provider_exists": provider_exists,
                "troubleshooting_hits": troubleshooting_hits,
                "successful_troubleshooting": successful_troubleshooting,
            },
        )

    def get_recommendation(self, confidence: float) -> Dict[str, Any]:
        """
        Get action recommendation based on confidence score.

        Args:
            confidence: Confidence score (0-1)

        Returns:
            Dictionary with recommendation details
        """
        if confidence >= self.THRESHOLD_HIGH:
            return {
                "action": "execute",
                "level": "high",
                "message": "High confidence - safe to auto-execute",
                "requires_approval": False,
            }
        elif confidence >= self.THRESHOLD_MEDIUM:
            return {
                "action": "execute_with_logging",
                "level": "medium",
                "message": "Medium confidence - execute with enhanced logging",
                "requires_approval": False,
            }
        elif confidence >= self.THRESHOLD_LOW:
            return {
                "action": "request_approval",
                "level": "low-medium",
                "message": "Low-medium confidence - request user approval",
                "requires_approval": True,
            }
        else:
            return {
                "action": "escalate",
                "level": "low",
                "message": "Low confidence - escalate to Calling LLM for guidance",
                "requires_approval": True,
            }

    def compute_from_rag_context(
        self, rag_context: Dict[str, Any], provider_exists: bool = False
    ) -> ConfidenceBreakdown:
        """
        Compute confidence from RAG context dictionary.

        Args:
            rag_context: Context from RAG queries
            provider_exists: Whether provider exists

        Returns:
            ConfidenceBreakdown
        """
        documents = rag_context.get("documents", [])
        troubleshooting = rag_context.get("troubleshooting", [])

        # Get max similarity from documents
        max_similarity = 0.0
        for doc in documents:
            similarity = doc.get("similarity", 0)
            if similarity > max_similarity:
                max_similarity = similarity

        # Count successful troubleshooting
        successful = sum(1 for ts in troubleshooting if ts.get("result") == "success")

        return self.compute_with_breakdown(
            rag_similarity=max_similarity,
            rag_hit_count=len(documents),
            provider_exists=provider_exists,
            troubleshooting_hits=len(troubleshooting),
            successful_troubleshooting=successful,
        )

    def adjust_for_task_complexity(self, base_confidence: float, task: str) -> float:
        """
        Adjust confidence based on task complexity.

        Complex tasks require higher confidence to execute.
        """
        # Simple heuristics for complexity
        complexity_keywords = {
            "high": ["migrate", "upgrade", "refactor", "rewrite", "redesign"],
            "medium": ["create", "implement", "modify", "update", "add"],
            "low": ["fix", "debug", "check", "test", "verify"],
        }

        task_lower = task.lower()

        # Detect complexity level
        complexity = "medium"
        for level, keywords in complexity_keywords.items():
            if any(kw in task_lower for kw in keywords):
                complexity = level
                break

        # Apply complexity adjustment
        adjustments = {
            "high": -0.15,  # High complexity reduces confidence
            "medium": 0.0,  # No adjustment
            "low": 0.10,  # Low complexity increases confidence
        }

        adjusted = base_confidence + adjustments.get(complexity, 0.0)
        return max(0.0, min(1.0, adjusted))


# Database-compatible confidence function (matches SQL function in schema)
def compute_confidence_score(
    rag_similarity: float,
    rag_hit_count: int,
    provider_exists: bool,
    similar_dag_exists: bool,
) -> float:
    """
    Compute confidence score compatible with database function.

    This matches the SQL function defined in 001-pgvector-schema.sql
    for consistency between Python and database calculations.

    Args:
        rag_similarity: Highest similarity score (0-1)
        rag_hit_count: Number of RAG hits
        provider_exists: Whether provider exists
        similar_dag_exists: Whether similar DAG exists

    Returns:
        Confidence score (0-1)
    """
    return (
        0.4 * (rag_similarity or 0)
        + 0.3 * min((rag_hit_count or 0) / 5.0, 1.0)
        + 0.2 * (1.0 if provider_exists else 0.0)
        + 0.1 * (1.0 if similar_dag_exists else 0.0)
    )


__version__ = "1.0.0"
__all__ = [
    "ConfidenceScorer",
    "ConfidenceWeights",
    "ConfidenceBreakdown",
    "compute_confidence_score",
]
