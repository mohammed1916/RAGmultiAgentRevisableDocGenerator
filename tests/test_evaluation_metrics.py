"""Unit tests for content evaluation metrics.

Tests ROUGE, BLEU, groundedness, context utilization, and semantic similarity.
"""

import pytest
from server.tools.evaluation_metrics import ContentEvaluator


class TestROUGE:
    """Test ROUGE score calculations."""

    def test_rouge_identical_text(self):
        """Test ROUGE with identical generated and reference text."""
        text = "The quick brown fox jumps over the lazy dog"
        scores = ContentEvaluator.calculate_rouge(text, text)

        assert scores["rouge1"] == 1.0
        assert scores["rouge2"] == 1.0
        assert scores["rougeL"] == 1.0

    def test_rouge_no_overlap(self):
        """Test ROUGE with completely different texts."""
        generated = "cat dog bird"
        reference = "apple orange banana"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        assert scores["rouge1"] == 0.0
        assert scores["rouge2"] == 0.0
        assert scores["rougeL"] == 0.0

    def test_rouge_partial_overlap(self):
        """Test ROUGE with partial overlap."""
        generated = "The cat is black"
        reference = "The cat is white"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        # "The", "cat", "is" are common - 3/4 = 0.75
        assert 0.5 <= scores["rouge1"] <= 1.0
        assert 0 <= scores["rouge2"] <= 1.0

    def test_rouge_empty_reference(self):
        """Test ROUGE with empty reference."""
        generated = "Some text"
        reference = ""
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        assert scores["rouge1"] == 0.0
        assert scores["rouge2"] == 0.0
        assert scores["rougeL"] == 0.0

    def test_rouge_case_insensitive(self):
        """Test that ROUGE is case-insensitive."""
        generated = "The Quick Brown Fox"
        reference = "the quick brown fox"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        assert scores["rouge1"] == 1.0


class TestBLEU:
    """Test BLEU score calculations."""

    def test_bleu_identical_text(self):
        """Test BLEU with identical texts."""
        text = "The quick brown fox jumps over the lazy dog"
        scores = ContentEvaluator.calculate_bleu(text, text)

        assert scores["bleu_1"] == 1.0
        assert scores["bleu_2"] == 1.0
        assert scores["bleu"] >= 0.9  # Should be very high

    def test_bleu_no_overlap(self):
        """Test BLEU with completely different texts."""
        generated = "cat dog bird"
        reference = "apple orange banana"
        scores = ContentEvaluator.calculate_bleu(generated, reference)

        assert scores["bleu_1"] == 0.0
        assert scores["bleu_2"] == 0.0
        assert scores["bleu"] == 0.0

    def test_bleu_partial_overlap(self):
        """Test BLEU with partial overlap."""
        generated = "the cat is black and white"
        reference = "the cat is white"
        scores = ContentEvaluator.calculate_bleu(generated, reference)

        # Generated is longer than reference but has overlap
        assert 0 <= scores["bleu"] <= 1.0
        assert 0 < scores["bleu_1"] <= 1.0

    def test_bleu_brevity_penalty(self):
        """Test BLEU brevity penalty for short generated text."""
        generated = "the cat"
        reference = "the cat is white"
        scores = ContentEvaluator.calculate_bleu(generated, reference)

        # Should have brevity penalty applied
        assert scores["bleu_1"] > 0
        assert scores["bleu"] < scores["bleu_1"]

    def test_bleu_empty_generated(self):
        """Test BLEU with empty generated text."""
        generated = ""
        reference = "some reference text"
        scores = ContentEvaluator.calculate_bleu(generated, reference)

        assert scores["bleu"] == 0.0


class TestGroundedness:
    """Test groundedness calculations."""

    def test_groundedness_fully_grounded(self):
        """Test groundedness with all tokens from context."""
        generated = "The cat is black"
        context = "The cat is black and white"
        result = ContentEvaluator.calculate_groundedness(generated, context)

        assert result["groundedness"] == 1.0
        assert result["grounded_tokens"] == 4
        assert result["total_tokens"] == 4

    def test_groundedness_ungrounded(self):
        """Test groundedness with no tokens from context."""
        generated = "apple orange banana"
        context = "cat dog bird"
        result = ContentEvaluator.calculate_groundedness(generated, context)

        assert result["groundedness"] == 0.0
        assert result["grounded_tokens"] == 0

    def test_groundedness_partial(self):
        """Test groundedness with partial overlap."""
        generated = "The cat is black"
        context = "The dog is white"
        result = ContentEvaluator.calculate_groundedness(generated, context)

        # "The" and "is" are grounded - 2/4 = 0.5
        assert 0 < result["groundedness"] < 1.0
        assert result["grounded_tokens"] > 0

    def test_groundedness_empty_context(self):
        """Test groundedness with empty context."""
        generated = "some text"
        context = ""
        result = ContentEvaluator.calculate_groundedness(generated, context)

        assert result["groundedness"] == 0.0


class TestContextUtilization:
    """Test context utilization calculations."""

    def test_context_utilization_full(self):
        """Test context utilization when all context is used."""
        generated = "The quick brown fox"
        context = "The quick brown fox"
        result = ContentEvaluator.calculate_context_utilization(generated, context)

        assert result["context_utilization"] == 1.0
        assert result["unique_context_tokens_used"] == 4

    def test_context_utilization_none(self):
        """Test context utilization when no context is used."""
        generated = "apple orange banana"
        context = "cat dog bird"
        result = ContentEvaluator.calculate_context_utilization(generated, context)

        assert result["context_utilization"] == 0.0
        assert result["unique_context_tokens_used"] == 0

    def test_context_utilization_partial(self):
        """Test context utilization with partial usage."""
        generated = "The cat is black"
        context = "The cat is black and white"
        result = ContentEvaluator.calculate_context_utilization(generated, context)

        # 4 out of 5 unique context tokens are used
        assert 0 < result["context_utilization"] < 1.0

    def test_context_utilization_empty_context(self):
        """Test context utilization with empty context."""
        generated = "some text"
        context = ""
        result = ContentEvaluator.calculate_context_utilization(generated, context)

        assert result["context_utilization"] == 0.0


class TestSemanticSimilarity:
    """Test semantic similarity calculations."""

    def test_semantic_similarity_identical(self):
        """Test semantic similarity with identical texts."""
        text = "The quick brown fox"
        result = ContentEvaluator.calculate_semantic_similarity(text, text)

        assert result["semantic_similarity"] == 1.0

    def test_semantic_similarity_no_overlap(self):
        """Test semantic similarity with no overlap."""
        generated = "cat dog bird"
        reference = "apple orange banana"
        result = ContentEvaluator.calculate_semantic_similarity(generated, reference)

        assert result["semantic_similarity"] == 0.0

    def test_semantic_similarity_partial(self):
        """Test semantic similarity with partial overlap."""
        generated = "The cat is black"
        reference = "The dog is white"
        result = ContentEvaluator.calculate_semantic_similarity(generated, reference)

        # "The" and "is" overlap
        assert 0 < result["semantic_similarity"] < 1.0

    def test_semantic_similarity_empty(self):
        """Test semantic similarity with empty texts."""
        result = ContentEvaluator.calculate_semantic_similarity("", "some text")
        assert result["semantic_similarity"] == 0.0


class TestComprehensiveEvaluation:
    """Test comprehensive evaluation combining multiple metrics."""

    def test_comprehensive_evaluation_good_content(self):
        """Test comprehensive evaluation with good generated content."""
        generated = "The quick brown fox jumps over the lazy dog"
        reference = "The quick brown fox jumps over the lazy dog"
        context = "Animal behavior: The quick brown fox is known for jumping over obstacles with speed"

        result = ContentEvaluator.comprehensive_evaluation(generated, reference, context)

        # Should have high scores
        assert result["rouge"]["rouge1"] > 0.8
        assert result["bleu"]["bleu"] > 0.8
        assert result["groundedness"]["groundedness"] >= 0.5  # Most content is grounded
        assert result["context_utilization"]["context_utilization"] >= 0.3
        assert result["overall_evaluation_score"] > 0.7

    def test_comprehensive_evaluation_poor_content(self):
        """Test comprehensive evaluation with poor generated content."""
        generated = "apple orange banana"
        reference = "The quick brown fox jumps over the lazy dog"
        context = "Information about animals and their behavior"

        result = ContentEvaluator.comprehensive_evaluation(generated, reference, context)

        # Should have low scores
        assert result["rouge"]["rouge1"] == 0.0
        assert result["bleu"]["bleu"] == 0.0
        assert result["overall_evaluation_score"] < 0.3

    def test_comprehensive_evaluation_without_context(self):
        """Test comprehensive evaluation without context."""
        generated = "The cat is black"
        reference = "The cat is white"

        result = ContentEvaluator.comprehensive_evaluation(generated, reference)

        # Should have rouge, bleu, semantic similarity but no groundedness
        assert "rouge" in result
        assert "bleu" in result
        assert "semantic_similarity" in result
        assert "groundedness" not in result
        assert "context_utilization" not in result
        assert "overall_evaluation_score" in result

    def test_comprehensive_evaluation_with_context(self):
        """Test comprehensive evaluation with context."""
        generated = "The cat is black"
        reference = "The cat is black"
        context = "The cat is black and white"

        result = ContentEvaluator.comprehensive_evaluation(generated, reference, context)

        # Should have all metrics
        assert "rouge" in result
        assert "bleu" in result
        assert "groundedness" in result
        assert "context_utilization" in result
        assert "overall_evaluation_score" in result

        assert result["groundedness"]["groundedness"] > 0.5
        assert result["context_utilization"]["context_utilization"] > 0.5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_text(self):
        """Test with very long text."""
        generated = " ".join(["word"] * 1000)
        reference = " ".join(["word"] * 1000)

        scores = ContentEvaluator.calculate_rouge(generated, reference)
        assert scores["rouge1"] == 1.0

    def test_single_word(self):
        """Test with single word texts."""
        scores = ContentEvaluator.calculate_rouge("cat", "cat")
        assert scores["rouge1"] == 1.0

    def test_punctuation_handling(self):
        """Test punctuation handling."""
        generated = "The cat is black."
        reference = "The cat is black"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        # Punctuation treated as separate token
        assert scores["rouge1"] < 1.0

    def test_special_characters(self):
        """Test with special characters."""
        generated = "hello@world.com test#123"
        reference = "hello@world.com test#123"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        assert scores["rouge1"] == 1.0

    def test_numeric_content(self):
        """Test with numeric content."""
        generated = "123 456 789"
        reference = "123 456 789"
        scores = ContentEvaluator.calculate_rouge(generated, reference)

        assert scores["rouge1"] == 1.0


class TestMetricsConsistency:
    """Test consistency and relationships between metrics."""

    def test_identical_text_all_metrics_high(self):
        """Test that identical texts score high on all metrics."""
        text = "The quick brown fox jumps over the lazy dog"

        result = ContentEvaluator.comprehensive_evaluation(text, text, text)

        assert result["rouge"]["rouge1"] == 1.0
        assert result["bleu"]["bleu"] > 0.9
        assert result["semantic_similarity"]["semantic_similarity"] == 1.0
        assert result["groundedness"]["groundedness"] == 1.0

    def test_different_text_metrics_consistency(self):
        """Test that different texts score low consistently."""
        generated = "apple orange"
        reference = "cat dog"

        result = ContentEvaluator.comprehensive_evaluation(generated, reference)

        assert result["rouge"]["rouge1"] == 0.0
        assert result["bleu"]["bleu"] == 0.0
        assert result["semantic_similarity"]["semantic_similarity"] == 0.0

    def test_rouge_bleu_relationship(self):
        """Test that ROUGE and BLEU scores correlate."""
        # High overlap should give high scores on both
        generated = "The cat is black"
        reference = "The cat is black"

        rouge = ContentEvaluator.calculate_rouge(generated, reference)
        bleu = ContentEvaluator.calculate_bleu(generated, reference)

        assert rouge["rouge1"] > 0.8
        assert bleu["bleu"] > 0.8

        # Low overlap should give low scores on both
        generated = "apple"
        reference = "orange"

        rouge = ContentEvaluator.calculate_rouge(generated, reference)
        bleu = ContentEvaluator.calculate_bleu(generated, reference)

        assert rouge["rouge1"] == 0.0
        assert bleu["bleu"] == 0.0
