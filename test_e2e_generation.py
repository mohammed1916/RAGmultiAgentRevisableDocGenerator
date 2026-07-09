#!/usr/bin/env python3
"""End-to-end test: Chat -> Document Generation"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from server.chat_orchestrator import ChatOrchestrator
from server.orchestrator import Orchestrator
from server.models import DocumentRequest

def safe_print(text):
    """Print safely with Unicode handling."""
    print(text.encode('utf-8', errors='replace').decode('utf-8'))

def test_e2e():
    """Test complete flow: Chat -> Document."""
    print("="*70)
    print("End-to-End Test: Chat + Document Generation")
    print("="*70)

    # Verify cloud config
    mode = os.getenv('OLLAMA_MODE')
    url = os.getenv('OLLAMA_BASE_URL')
    print(f"\nMode: {mode}")
    print(f"URL: {url}")

    chat = ChatOrchestrator()
    doc_gen = Orchestrator()

    # Simulate quick conversation
    print("\n[STEP 1] User initiates")
    print('[INPUT] "I want to prepare for JEE exam in 60 days"')
    r1 = chat.start_conversation("I want to prepare for JEE exam in 60 days")
    safe_print(f"[LLM] {r1.message[:120]}...\n")

    ctx = r1.context

    # Quick answers to get to [READY]
    answers = [
        ("Physics, Chemistry, Maths", "which subjects"),
        ("Mechanics, Kinematics, Thermodynamics", "which topics"),
    ]

    for answer, desc in answers:
        print(f"[INPUT #{answers.index((answer, desc))+2}] {answer}")
        r = chat.add_answer(ctx, "user_input", answer)
        safe_print(f"[LLM] {r.message[:120]}...\n")
        ctx = r.context

        # Check for [READY]
        if "[READY]" in r.message:
            print("[SUCCESS] LLM marked [READY]!")
            break

    # Now generate document
    if r.is_ready_to_generate:
        print("\n[STEP 2] Generating Document from Chat Context")
        print("[ACTION] Building generation prompt...")

        try:
            prompt = chat.get_generation_prompt(ctx)
            print(f"[PROMPT LENGTH] {len(prompt)} chars")

            print("[ACTION] Calling orchestrator.generate_document()...")
            doc_request = DocumentRequest(request=prompt)
            response = doc_gen.generate_document(doc_request)

            print(f"\n[RESULT] SUCCESS!")
            print(f"  Filename: {response.document_filename}")
            print(f"  Size: {Path('output') / response.document_filename}")

            # Check if file exists
            filepath = Path('output') / response.document_filename
            if filepath.exists():
                size_kb = filepath.stat().st_size / 1024
                print(f"  File size: {size_kb:.1f} KB")
                print(f"  File type: {filepath.suffix}")

                # Try to read content
                try:
                    from docx import Document
                    doc = Document(filepath)
                    print(f"\n[DOCUMENT CONTENT]")
                    para_count = 0
                    char_count = 0
                    for para in doc.paragraphs[:20]:
                        if para.text.strip():
                            para_count += 1
                            char_count += len(para.text)
                            if para_count <= 3:
                                safe_print(f"  {para.text[:80]}")

                    print(f"\n  Total: {para_count} paragraphs, {char_count} chars")

                    if char_count > 500:
                        print("\n[VERDICT] YES - Real content generated!")
                    else:
                        print("\n[VERDICT] Document exists but minimal content")

                except Exception as e:
                    print(f"\n[WARNING] Could not read DOCX: {e}")
                    print("[VERDICT] File created, but content check failed")
            else:
                print(f"\n[ERROR] File not found at {filepath}")

        except Exception as e:
            print(f"\n[ERROR] Document generation failed:")
            print(f"  {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[INCOMPLETE] Did not reach [READY] state after answers")

if __name__ == "__main__":
    test_e2e()
