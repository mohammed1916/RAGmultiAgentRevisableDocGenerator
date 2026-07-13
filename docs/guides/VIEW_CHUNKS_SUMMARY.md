================================================================================
MILVUS CHUNK VIEWER - COMPLETE GUIDE
================================================================================

YES - You CAN view and search chunks in Milvus!

Tool: scripts/view_chunks.py
Status: Fixed and ready to use
Features: Search, browse, filter, inspect, and manage chunks

================================================================================
AVAILABLE COMMANDS
================================================================================

1. VIEW STATISTICS (Check if data loaded)
   $ python scripts/view_chunks.py --stats

   Shows:
     - Milvus mode (MILVUS)
     - Total chunks stored (currently: 0)
     - Index status
     - Collection name

2. SEARCH CHUNKS (Find by keyword)
   $ python scripts/view_chunks.py --search "electric field"
   $ python scripts/view_chunks.py --search "Coulomb" --top-k 5

   Returns: Matching chunks with relevance scores

3. LIST ALL CHUNKS (View everything)
   $ python scripts/view_chunks.py --all
   $ python scripts/view_chunks.py --all -v  (with full content)

   Returns: Table of all stored chunks

4. FILTER BY TYPE (Find specific subject)
   $ python scripts/view_chunks.py --type jee_physics
   $ python scripts/view_chunks.py --type cbse_science

   Returns: Chunks of that type only

5. VIEW SPECIFIC CHUNK (See full details)
   $ python scripts/view_chunks.py --id elec_001

   Returns: Complete chunk with metadata and content

6. LOAD MOCK DATA (For testing)
   $ python scripts/view_chunks.py --load-mock

   Loads 10 sample chunks for testing the viewer

================================================================================
CURRENT STATUS
================================================================================

Milvus: Connected
Database: documents
Mode: MILVUS (production)
Total Chunks: 0 (empty - need to load curriculum)
Indexed: YES

================================================================================
HOW TO USE IT
================================================================================

STEP 1: Check status
$ python scripts/view_chunks.py --stats
  Response: Mode: MILVUS, Total Chunks: 0, Indexed: OK

STEP 2: Load curriculum data
$ python load_curriculum.py
  This will populate Milvus with 800+ chunks

STEP 3: Verify loaded
$ python scripts/view_chunks.py --stats
  Response should show: Total Chunks: 847+ (or whatever you loaded)

STEP 4: Search for topics used in RAG testing
$ python scripts/view_chunks.py --search "electrostatics"
$ python scripts/view_chunks.py --search "Coulomb's law" --top-k 3
$ python scripts/view_chunks.py --search "electric field"

  Check: Are results relevant? Scores > 0.7?

STEP 5: View details of a specific chunk
$ python scripts/view_chunks.py --id [chunk_id_from_search]

STEP 6: Run quality tests
$ python scripts/test_rag_quality.py

  This will use the retrieved chunks for evaluation

================================================================================
EXAMPLE WORKFLOW - DEBUGGING RAG QUALITY
================================================================================

Problem: RAG quality tests showing low scores
Solution: Check what chunks are being retrieved

1. Test search for topics in your test prompts:
   $ python scripts/view_chunks.py --search "electric field"
   $ python scripts/view_chunks.py --search "Coulomb's law"
   $ python scripts/view_chunks.py --search "equipotential"

2. Check relevance scores:
   If scores < 0.5:
     → Chunks not relevant
     → Search algorithm needs tuning
     → Curriculum data may be poorly formatted

   If scores > 0.7:
     → Retrieval looks good
     → Check if LLM is using the chunks (groundedness metric)

3. View a highly relevant chunk to understand quality:
   $ python scripts/view_chunks.py --id [best_chunk_id]

   Check: Is content clear? Is format good? Useful for LLM?

4. Compare multiple chunks:
   $ python scripts/view_chunks.py --search "field" --top-k 10

   Check: Do all top results make sense? Is there noise?

================================================================================
INTEGRATION WITH TESTING
================================================================================

BEFORE Running Quality Tests:
  - python scripts/view_chunks.py --stats
    Verify chunks loaded (Total > 0)

  - python scripts/view_chunks.py --search "test_topic1"
    Verify retrieval works for your topics

  - python scripts/view_chunks.py --search "test_topic2" --top-k 5
    Check relevance scores > 0.7

DURING Quality Tests:
  - python scripts/test_rag_quality.py
    Automatically uses retrieved chunks

AFTER Quality Tests:
  - python scripts/view_chunks.py --search "topic_from_failing_test"
    See what chunks were retrieved

  - python scripts/view_chunks.py --id [chunk_id]
    Inspect full chunk content

  - Analyze: Is retriever working? Are chunks relevant?

================================================================================
SEARCH COMMANDS FOR PHYSICS CURRICULUM
================================================================================

Electric Field Topics:
  python scripts/view_chunks.py --search "electric field"
  python scripts/view_chunks.py --search "field lines"
  python scripts/view_chunks.py --search "field strength"

Coulomb's Law:
  python scripts/view_chunks.py --search "Coulomb's law"
  python scripts/view_chunks.py --search "point charges"
  python scripts/view_chunks.py --search "force between charges"

Potential & Capacitance:
  python scripts/view_chunks.py --search "electric potential"
  python scripts/view_chunks.py --search "capacitance"
  python scripts/view_chunks.py --search "potential energy"

Conductors & Dielectrics:
  python scripts/view_chunks.py --search "conductor"
  python scripts/view_chunks.py --search "dielectric"
  python scripts/view_chunks.py --search "equipotential"

Gauss's Law:
  python scripts/view_chunks.py --search "Gauss's law"
  python scripts/view_chunks.py --search "flux"
  python scripts/view_chunks.py --search "surface charge"

================================================================================
QUICK REFERENCE
================================================================================

Check if data loaded:
  python scripts/view_chunks.py --stats

Search for a topic:
  python scripts/view_chunks.py --search "topic" --top-k 5

View all chunks:
  python scripts/view_chunks.py --all

See full chunk content:
  python scripts/view_chunks.py --id chunk_001

Load test data:
  python scripts/view_chunks.py --load-mock

================================================================================
NEXT STEPS
================================================================================

1. Verify Milvus is working:
   $ python scripts/view_chunks.py --stats

2. Load curriculum data:
   $ python load_curriculum.py

3. Verify it loaded:
   $ python scripts/view_chunks.py --stats
   (should show Total Chunks > 0)

4. Test searches for your topics:
   $ python scripts/view_chunks.py --search "electrostatics"
   $ python scripts/view_chunks.py --search "Coulomb"

5. Check search quality:
   $ python scripts/view_chunks.py --search "electric field" --top-k 5
   (look for scores > 0.7 and relevant results)

6. Run quality tests:
   $ python scripts/test_rag_quality.py

7. If metrics are low, debug with:
   $ python scripts/view_chunks.py --search "failing_topic" --top-k 10

================================================================================
