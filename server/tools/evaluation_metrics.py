"""Evaluation metrics for generated content quality.

Implements ROUGE, BLEU, groundedness, and context utilization metrics.
"""

from typing import List, Dict, Any
from collections import Counter
import math

from ..logger import setup_logger

logger = setup_logger(__name__)


class ContentEvaluator:
    """Evaluate generated content quality using multiple metrics."""

    @staticmethod
    def calculate_rouge(generated: str, reference: str) -> Dict[str, float]:
        """Calculate ROUGE scores (Recall-Oriented Understudy for Gisting Evaluation).

        ROUGE-1, ROUGE-2, ROUGE-L scores measure n-gram overlap.

        Args:
            generated: Generated text
            reference: Reference/ground truth text

        Returns:
            Dictionary with rouge1, rouge2, rougeL scores (0-1)
        """
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not ref_tokens:
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

        # ROUGE-1 (unigram overlap)
        gen_unigrams = set(gen_tokens)
        ref_unigrams = set(ref_tokens)
        rouge1 = (
            len(gen_unigrams & ref_unigrams) / len(ref_unigrams)
            if ref_unigrams
            else 0.0
        )

        # ROUGE-2 (bigram overlap)
        gen_bigrams = set(zip(gen_tokens, gen_tokens[1:]))
        ref_bigrams = set(zip(ref_tokens, ref_tokens[1:]))
        rouge2 = (
            len(gen_bigrams & ref_bigrams) / len(ref_bigrams)
            if ref_bigrams
            else 0.0
        )

        # ROUGE-L (Longest Common Subsequence)
        rougeL = ContentEvaluator._longest_common_subsequence_ratio(
            gen_tokens, ref_tokens
        )

        return {
            "rouge1": round(rouge1, 4),
            "rouge2": round(rouge2, 4),
            "rougeL": round(rougeL, 4),
        }

    @staticmethod
    def calculate_bleu(generated: str, reference: str, max_n: int = 4) -> Dict[str, float]:
        """Calculate BLEU score (Bilingual Evaluation Understudy).

        BLEU measures n-gram precision with brevity penalty.

        Args:
            generated: Generated text
            reference: Reference text
            max_n: Maximum n-gram size (default 4)

        Returns:
            Dictionary with bleu score and individual n-gram precisions
        """
        gen_tokens = generated.lower().split()
        ref_tokens = reference.lower().split()

        if not gen_tokens or not ref_tokens:
            return {f"bleu_{i}": 0.0 for i in range(1, max_n + 1)} | {"bleu": 0.0}

        bleu_scores = {}
        precisions = []

        for n in range(1, max_n + 1):
            if len(gen_tokens) < n or len(ref_tokens) < n:
                bleu_scores[f"bleu_{n}"] = 0.0
                precisions.append(0.0)
                continue

            gen_ngrams = Counter(
                tuple(gen_tokens[i : i + n]) for i in range(len(gen_tokens) - n + 1)
            )
            ref_ngrams = Counter(
                tuple(ref_tokens[i : i + n]) for i in range(len(ref_tokens) - n + 1)
            )

            # Clip counts
            common = sum(
                min(gen_ngrams[ngram], ref_ngrams[ngram])
                for ngram in gen_ngrams
                if ngram in ref_ngrams
            )

            precision = common / sum(gen_ngrams.values()) if gen_ngrams else 0.0
            bleu_scores[f"bleu_{n}"] = round(precision, 4)
            precisions.append(precision)

        # Brevity penalty
        if len(gen_tokens) > 0 and len(ref_tokens) > 0:
            brevity_penalty = (
                1.0
                if len(gen_tokens) >= len(ref_tokens)
                else math.exp(1 - len(ref_tokens) / len(gen_tokens))
            )
        else:
            brevity_penalty = 0.0

        # Geometric mean of precisions
        if all(p > 0 for p in precisions):
            bleu = brevity_penalty * math.exp(
                sum(math.log(p) for p in precisions) / len(precisions)
            )
        else:
            bleu = 0.0

        bleu_scores["bleu"] = round(bleu, 4)
        return bleu_scores

    @staticmethod
    def calculate_groundedness(
        generated: str, context: str, threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Calculate groundedness - measure of how grounded generated text is in context.

        Checks what percentage of generated content can be traced back to context.

        Args:
            generated: Generated text
            context: Source context/reference material
            threshold: Minimum overlap ratio to consider grounded (0-1)

        Returns:
            Dictionary with groundedness score and grounded/ungrounded phrases
        """
        gen_tokens = generated.lower().split()
        context_tokens = context.lower().split()

        if not gen_tokens or not context_tokens:
            return {
                "groundedness": 0.0,
                "grounded_tokens": 0,
                "total_tokens": len(gen_tokens),
            }

        context_set = set(context_tokens)
        grounded_count = sum(1 for token in gen_tokens if token in context_set)
        groundedness = grounded_count / len(gen_tokens) if gen_tokens else 0.0

        return {
            "groundedness": round(groundedness, 4),
            "grounded_tokens": grounded_count,
            "total_tokens": len(gen_tokens),
            "grounded_ratio": round(
                grounded_count / len(gen_tokens), 4
            ) if gen_tokens else 0.0,
        }

    @staticmethod
    def calculate_context_utilization(
        generated: str, context: str
    ) -> Dict[str, Any]:
        """Calculate context utilization - how much of the context is used.

        Measures coverage of context in generated output.

        Args:
            generated: Generated text
            context: Source context

        Returns:
            Dictionary with utilization metrics
        """
        gen_tokens = set(generated.lower().split())
        context_tokens = set(context.lower().split())

        if not context_tokens:
            return {
                "context_utilization": 0.0,
                "unique_context_tokens_used": 0,
                "total_context_tokens": 0,
            }

        # How many unique context tokens appear in generated
        used = len(gen_tokens & context_tokens)
        total = len(context_tokens)

        utilization = used / total if total > 0 else 0.0

        return {
            "context_utilization": round(utilization, 4),
            "unique_context_tokens_used": used,
            "total_context_tokens": total,
        }

    @staticmethod
    def calculate_semantic_similarity(
        generated: str, reference: str
    ) -> Dict[str, float]:
        """Calculate semantic similarity using simple word overlap.

        Note: For production, use sentence transformers or similar.

        Args:
            generated: Generated text
            reference: Reference text

        Returns:
            Dictionary with similarity score
        """
        gen_words = set(generated.lower().split())
        ref_words = set(reference.lower().split())

        if not gen_words or not ref_words:
            return {"semantic_similarity": 0.0}

        intersection = len(gen_words & ref_words)
        union = len(gen_words | ref_words)

        jaccard = intersection / union if union > 0 else 0.0

        return {"semantic_similarity": round(jaccard, 4)}

    @staticmethod
    def comprehensive_evaluation(
        generated: str, reference: str, context: str = None
    ) -> Dict[str, Any]:
        """Run comprehensive evaluation across all metrics.

        Args:
            generated: Generated text
            reference: Reference/ground truth text
            context: Optional source context

        Returns:
            Dictionary with all evaluation metrics
        """
        logger.info("Running comprehensive content evaluation")

        results = {
            "rouge": ContentEvaluator.calculate_rouge(generated, reference),
            "bleu": ContentEvaluator.calculate_bleu(generated, reference),
            "semantic_similarity": ContentEvaluator.calculate_semantic_similarity(
                generated, reference
            ),
        }

        if context:
            results["groundedness"] = ContentEvaluator.calculate_groundedness(
                generated, context
            )
            results["context_utilization"] = (
                ContentEvaluator.calculate_context_utilization(generated, context)
            )

        # Calculate overall score (weighted average)
        overall_score = (
            results["rouge"]["rouge1"] * 0.25
            + results["rouge"]["rouge2"] * 0.25
            + results["bleu"]["bleu"] * 0.25
            + results["semantic_similarity"]["semantic_similarity"] * 0.25
        )

        if context:
            overall_score = (
                overall_score * 0.7
                + results["groundedness"]["groundedness"] * 0.3
            )

        results["overall_evaluation_score"] = round(overall_score, 4)

        logger.info(f"Evaluation complete. Overall score: {overall_score:.4f}")
        return results

    @staticmethod
    def _longest_common_subsequence_ratio(seq1: List, seq2: List) -> float:
        """Calculate LCS ratio for ROUGE-L calculation."""
        lcs_len = ContentEvaluator._lcs_length(seq1, seq2)
        if not seq2:
            return 0.0
        return lcs_len / len(seq2)

    @staticmethod
    def _lcs_length(seq1: List, seq2: List) -> int:
        """Calculate longest common subsequence length."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]
