# Memory Architecture

## 1. Overview

The memory architecture provides long-term personalization for the AI learning platform.

Unlike traditional chat systems where every conversation is temporary, this system continuously learns from user interactions, study behavior, mistakes, preferences, and progress.

Memory enables the AI system to understand:

- What the user knows
- What the user struggles with
- How the user prefers learning
- What concepts require revision
- Previous interactions and decisions

The memory system acts as the long-term intelligence layer shared across AI agents.

---

# 2. Memory Architecture Overview

```text
                    User Interaction

                           |
                           v

                  Memory Extraction Layer

                           |
          +----------------+----------------+

          |                                 |

   Short-Term Memory                Long-Term Memory

          |                                 |

 Current Conversation          User Knowledge History

          |                                 |

          +----------------+----------------+

                           |

                    Memory Storage

          +----------------+----------------+

          |                                 |

      Vector Memory                 Structured Memory

        Milvus                          PostgreSQL

          |                                 |

 Semantic Recall              User State / Metadata

                           |

                    AI Agents
```

---

# 3. Memory Types

The platform uses multiple memory layers.

---

# 3.1 Short-Term Memory

Short-term memory stores information during an active session.

Examples:

- Current conversation
- Current topic
- Recent questions
- Temporary context
- Current learning objective

Example:

```text
User:

Explain Newton's second law.

Previous messages:

- User does not understand force calculation
- User requested simpler examples
```

This memory expires after the session.

---

# 3.2 Working Memory

Working memory maintains the active learning context.

Examples:

```text
Current Profile:

Class 12 Physics


Current Chapter:

Electrostatics


Current Goal:

Complete capacitance problems


Current Difficulty:

Intermediate
```

Working memory helps agents make immediate decisions.

---

# 3.3 Long-Term Memory

Long-term memory stores persistent user information.

Examples:

- Learning history
- Weak concepts
- Strong concepts
- Preferences
- Previous mistakes
- Study patterns
- Achievements

This memory remains available across sessions.

---

# 4. Memory Data Model

Every memory object contains:

```json
{
  "user_id": "abdullah",
  "profile_id": "class12",
  "type": "concept_weakness",
  "subject": "physics",
  "concept": "capacitance",
  "confidence": 0.35,
  "source": "quiz_attempt",
  "created_at": "2026-07-20"
}
```

---

# 5. Memory Categories

## 5.1 Knowledge Memory

Stores what the user knows.

Examples:

```text
Concept:

Ohm's Law

Status:

Mastered

Confidence:

0.92
```

---

## 5.2 Learning Difficulty Memory

Stores weak areas.

Example:

```text
Concept:

Capacitance

Evidence:

- Failed quiz attempts
- Multiple explanations requested
- Low confidence rating

Action:

Increase revision frequency
```

---

## 5.3 Preference Memory

Stores learning preferences.

Examples:

- Prefers visual explanations
- Prefers step-by-step solutions
- Prefers examples before theory
- Prefers concise answers

---

## 5.4 Behavioral Memory

Stores study patterns.

Examples:

- Average study duration
- Preferred study time
- Completion habits
- Revision consistency

---

## 5.5 Interaction Memory

Stores important previous conversations.

Examples:

```text
User previously asked:

"Explain Maxwell equations intuitively"

AI response:

Used analogy-based explanation.

User feedback:

Helpful.
```

---

# 6. Memory Extraction Pipeline

Every interaction passes through memory processing.

```text
User Interaction

        |

        v

Information Extractor

        |

        v

Memory Classifier

        |

        v

Importance Scoring

        |

        v

Memory Storage

        |

        v

Future Retrieval
```

---

# 7. Memory Importance Scoring

Not every interaction should become permanent memory.

The system evaluates:

```text
Memory Score =

User Importance

+

Future Usefulness

+

Learning Impact

+

Frequency
```

Examples:

High importance:

```text
User struggles with integration problems repeatedly.
```

Low importance:

```text
User asked a one-time definition.
```

---

# 8. Memory Storage Design

The system uses different storage mechanisms.

---

## 8.1 Vector Memory

Used for semantic recall.

Stores:

- Conversation summaries
- Explanations
- Learning experiences
- User insights

Technology:

- Milvus
- Qdrant

Example query:

```text
Find previous discussions about electromagnetic induction.
```

---

## 8.2 Structured Memory

Stores exact user state.

Examples:

- Scores
- Confidence values
- Revision dates
- Profile information

Technology:

- PostgreSQL
- SQLite

---

## 8.3 Knowledge Graph Memory

Stores relationships.

Example:

```text
Student

   |
   learns

Electrostatics

   |
   requires

Vectors

   |
   related_to

Force
```

Technologies:

- Neo4j
- NetworkX

---

# 9. Memory Retrieval

Memory retrieval is integrated into every AI request.

Example:

User:

```text
Explain current electricity.
```

Before answering:

```text
Retrieve:

- Previous physics knowledge
- Weak concepts
- Preferred explanation style
- Related topics
- Revision history
```

Then the AI generates a personalized response.

---

# 10. Agent Memory Integration

Different agents use different memory.

## Tutor Agent

Uses:

- Knowledge memory
- Preference memory
- Interaction history


## Planner Agent

Uses:

- Progress memory
- Weakness memory
- Schedule history


## Quiz Agent

Uses:

- Mistake memory
- Performance history


## Revision Agent

Uses:

- FSRS state
- Concept confidence
- Forgetting patterns

---

# 11. Memory Frameworks

Recommended technologies:

## Mem0

Purpose:

- Personal AI memory layer
- Automatic memory extraction
- Semantic recall


## LangGraph Memory

Purpose:

- Agent state management
- Workflow persistence


## Zep

Purpose:

- Long-term conversational memory

---

# 12. Privacy and Isolation

Memory must always respect user boundaries.

Every memory object is isolated using:

```text
user_id

+

profile_id
```

Example:

```text
Class 10 Mathematics memory

cannot affect

Class 12 Physics memory
```

unless explicitly shared.

---

# 13. Memory Lifecycle

```text
Create

  |

Extract

  |

Evaluate

  |

Store

  |

Retrieve

  |

Update

  |

Archive
```

Memory continuously evolves as the student learns.

---

# 14. Future Improvements

Possible extensions:

- Automatic forgetting of outdated memories
- Memory confidence decay
- Self-correcting memory updates
- Cross-profile knowledge transfer
- Personalized learning predictions
- AI-generated learning summaries

---

# 15. Design Goals

The memory architecture should provide:

- Persistent personalization
- Learning awareness
- Agent continuity
- Adaptive recommendations
- Intelligent revision planning
- User-specific AI behavior

The memory system transforms the AI from a generic assistant into a personalized learning companion.