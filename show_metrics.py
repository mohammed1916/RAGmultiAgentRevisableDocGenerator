#!/usr/bin/env python
"""Display metrics on REAL generated content with Milvus RAG context."""

from server.orchestrator import Orchestrator
from server.models import DocumentRequest
from server.tools.evaluation_metrics import ContentEvaluator
from server.tools.milvus_rag import MilvusRAG

print("=" * 80)
print("EVALUATION METRICS WITH REAL MILVUS RAG + LLM-GENERATED CONTENT")
print("=" * 80)

# Initialize RAG to fetch real curriculum
print("\n[1] Initializing Milvus RAG (fetching curriculum)...")
rag = MilvusRAG()
curriculum_context = rag.search("Electrostatics electric charges", top_k=3)
print(
    f"    Fetched {len(curriculum_context)} curriculum documents from Milvus")

# Show what curriculum context we got
print("\n[2] Curriculum Context from Milvus:")
print("-" * 80)
for i, doc in enumerate(curriculum_context, 1):
    print(f"\nDocument {i}: {doc.get('id', 'Unknown')}")
    print(f"Content (first 200 chars): {doc.get('content', '')[:200]}...")

# Generate content using the orchestrator
print("\n" + "=" * 80)
print("[3] Generating Study Plan Content with Orchestrator...")
print("-" * 80)

request = DocumentRequest(
    request="Create a 3-day study plan for Electrostatics focusing on Coulomb's law and electric field",
    metadata={"subject": "Physics", "level": "JEE", "scope": "Electrostatics"}
)

orchestrator = Orchestrator()
result = orchestrator.generate_document(request)

print(f"✓ Document generated: {result.document_filename}")
print(f"  Document type: {result.execution_plan.document_type}")
print(f"  Outline: {result.execution_plan.outline}")
print(f"  Success: {result.success}")

# Build generated content from plan + tasks
generated_content = f"{result.execution_plan.document_type}\n"
generated_content += "\n".join(result.execution_plan.outline) + "\n"
generated_content += "\n".join(
    [f"Task {t.id}: {t.description}" for t in result.execution_plan.tasks])

print("\n[4] Generated Content Preview:")
print("-" * 80)
print(generated_content[:500])
print("...[content continues]...\n")

# Calculate metrics
print("=" * 80)
print("[5] CALCULATING METRICS ON GENERATED CONTENT")
print("=" * 80)

# Combine curriculum context into one string
combined_curriculum = " ".join([doc.get('content', '')
                               for doc in curriculum_context])

# ROUGE - how much overlap with curriculum
print("\n[ROUGE] - Overlap between generated and curriculum:")
rouge = ContentEvaluator.calculate_rouge(
    generated_content, combined_curriculum)
print(f"  ROUGE-1 (unigrams):    {rouge['rouge1']:.4f}")
print(f"  ROUGE-2 (bigrams):     {rouge['rouge2']:.4f}")
print(f"  ROUGE-L (subsequence): {rouge['rougeL']:.4f}")
print(
    f"  --> Generated content has {rouge['rouge1']*100:.1f}% word overlap with curriculum")

# BLEU - precision of match with curriculum
print("\n[BLEU] - Precision of generated content vs curriculum:")
bleu = ContentEvaluator.calculate_bleu(generated_content, combined_curriculum)
print(f"  BLEU-1 (unigrams):     {bleu['bleu_1']:.4f}")
print(f"  BLEU-2 (bigrams):      {bleu['bleu_2']:.4f}")
print(f"  BLEU-3 (trigrams):     {bleu['bleu_3']:.4f}")
print(f"  BLEU-4 (4-grams):      {bleu['bleu_4']:.4f}")
print(f"  Final BLEU Score:      {bleu['bleu']:.4f}")
print(f"  --> {bleu['bleu']*100:.1f}% precision match with curriculum")

# Groundedness - what % of generated text is grounded in curriculum
print("\n[GROUNDEDNESS] - Is generated content grounded in curriculum?")
groundedness = ContentEvaluator.calculate_groundedness(
    generated_content, combined_curriculum)
print(
    f"  Groundedness Score:    {groundedness['groundedness']:.4f} ({groundedness['groundedness']*100:.1f}%)")
print(
    f"  Grounded tokens:       {groundedness['grounded_tokens']}/{groundedness['total_tokens']}")
print(
    f"  --> {groundedness['groundedness']*100:.1f}% of generated text appears in curriculum (non-hallucination score)")

# Context Utilization - how much of curriculum is used
print("\n[CONTEXT UTILIZATION] - How much of fetched curriculum is used?")
util = ContentEvaluator.calculate_context_utilization(
    generated_content, combined_curriculum)
print(
    f"  Context Utilization:   {util['context_utilization']:.4f} ({util['context_utilization']*100:.1f}%)")
print(
    f"  Curriculum terms used: {util['unique_context_tokens_used']}/{util['total_context_tokens']}")
print(
    f"  --> Generated content uses {util['context_utilization']*100:.1f}% of available curriculum context")

# Quality scores from orchestrator
print("\n" + "=" * 80)
print("[6] QUALITY SCORES FROM ORCHESTRATOR REVIEW")
print("=" * 80)
if result.quality_scores:
    print(f"  Relevance:    {result.quality_scores.relevance}/5")
    print(f"  Completeness: {result.quality_scores.completeness}/5")
    print(f"  Coherence:    {result.quality_scores.coherence}/5")
    print(f"  Structure:    {result.quality_scores.structure}/5")
    print(f"  Overall:      {result.quality_scores.overall}/5")
else:
    print("  No quality scores available")

# Execution metrics
print("\n" + "=" * 80)
print("[7] EXECUTION METRICS")
print("=" * 80)
print(f"  Planner latency:       {result.metrics.planner_latency_ms:.0f} ms")
print(f"  Writer latency:        {result.metrics.writer_latency_ms:.0f} ms")
print(f"  Reviewer latency:      {result.metrics.reviewer_latency_ms:.0f} ms")
print(
    f"  DOCX generation:       {result.metrics.docx_generation_latency_ms:.0f} ms")
print(
    f"  Total execution time:  {result.metrics.total_execution_time_ms:.0f} ms ({result.metrics.total_execution_time_ms/1000:.1f}s)")
print(f"  Review iterations:     {result.metrics.review_iterations}")

print("\n" + "=" * 80)
print("[COMPLETE] Real-world Metrics Display Finished")
print("=" * 80)
print(f"\nDocument saved to: output/{result.document_filename}")
