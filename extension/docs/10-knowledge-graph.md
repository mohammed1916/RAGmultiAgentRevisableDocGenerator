# Knowledge Graph

## 1. Overview

The knowledge graph represents relationships between concepts, documents, skills, and learning objectives.

Unlike traditional folder-based organization, the knowledge graph models how knowledge is connected.

The graph enables the AI system to understand:

- Concept dependencies
- Learning prerequisites
- Related topics
- Knowledge gaps
- Learning paths
- Recommended next steps

The knowledge graph acts as the reasoning layer of the learning platform.

---

# 2. Knowledge Graph Architecture

```text
                  Knowledge Graph

                         |
        +----------------+----------------+

        |                                 |

   Concept Nodes                  Relationship Edges

        |                                 |

 Subjects, Topics,             Requires
 Chapters, Skills              Related To
 Documents                     Part Of
 Questions                     Mastered By

                         |

                    AI Reasoning

                         |

              Personalized Learning Path
```

---

# 3. Knowledge Representation

The graph consists of nodes and relationships.

## 3.1 Nodes

Nodes represent entities in the learning system.

Examples:

```text
Physics

   |
   +-- Electrostatics

          |
          +-- Electric Field

          |
          +-- Capacitance

          |
          +-- Current Electricity
```

Node types:

- Subject
- Chapter
- Concept
- Formula
- Question
- Document
- Skill
- Learning Objective
- User Knowledge State

---

## 3.2 Relationships

Relationships describe how nodes are connected.

Examples:

```text
Electrostatics

        requires

Vectors


Capacitance

        related_to

Potential Difference


Newton's Laws

        prerequisite_for

Momentum
```

Relationship types:

- Requires
- Prerequisite Of
- Related To
- Part Of
- Explained By
- Tested By
- Mastered By
- Weak In

---

# 4. Learning Dependency Graph

Concepts are not independent.

The graph stores prerequisite relationships.

Example:

```text
Mathematics

    |
    v

Algebra

    |
    v

Functions

    |
    v

Calculus

    |
    v

Integration
```

Before teaching a concept, the AI checks prerequisite knowledge.

---

# 5. User Knowledge Graph

Each user has a personalized knowledge state.

Example:

```text
                Student

                   |

          +--------+--------+

          |                 |

     Electrostatics      Magnetism

          |                 |

     Confidence: 0.8    Confidence: 0.4

          |                 |

      Mastered          Needs Revision
```

The graph combines:

- Concept understanding
- Confidence scores
- Learning history
- Mistakes
- Revision status

---

# 6. Knowledge Graph Construction

The graph is created from multiple sources.

## 6.1 Document Extraction

Documents are analyzed to extract:

- Concepts
- Topics
- Relationships
- References

Example:

Input:

```text
NCERT Physics Chapter: Electrostatics
```

Extracted:

```text
Electrostatic Force

    related_to

Electric Field

    related_to

Potential Difference
```

---

## 6.2 AI Generated Relationships

LLMs can identify missing connections.

Example:

```text
User learned:

Ohm's Law


AI identifies:

Requires understanding of:

- Voltage
- Current
- Resistance
```

---

## 6.3 User Interaction Data

Interactions continuously update the graph.

Example:

```text
User repeatedly fails capacitor problems.

        |

Graph update:

Capacitance confidence decreases.

        |

Planner schedules revision.
```

---

# 7. Graph-Based Retrieval

The knowledge graph improves RAG retrieval.

Traditional retrieval:

```text
Query

   |

Search documents

   |

Return chunks
```

Graph-enhanced retrieval:

```text
Query

   |

Find concept

   |

Traverse related concepts

   |

Retrieve connected documents

   |

Generate answer
```

---

# 8. Prerequisite Reasoning

The AI can determine required background knowledge.

Example:

User:

```text
Explain Current Electricity.
```

Graph traversal:

```text
Current Electricity

        |
        requires

Electric Charge

        |
        requires

Electrostatic Concepts
```

The AI can provide prerequisite explanations automatically.

---

# 9. Learning Path Generation

The graph enables adaptive learning paths.

Example:

Goal:

```text
Learn Calculus
```

Generated path:

```text
Arithmetic

      |

Algebra

      |

Functions

      |

Limits

      |

Derivatives

      |

Integration
```

The path changes based on user knowledge state.

---

# 10. Knowledge Gap Detection

The system identifies missing concepts.

Example:

```text
User understands:

Force

Acceleration


User struggles with:

Momentum


Graph analysis:

Missing connection between:

Force -> Momentum
```

The planner recommends targeted learning.

---

# 11. Graph Visualization

The frontend provides interactive graph exploration.

Technologies:

## React Flow

Used for:

- Learning roadmap
- Concept maps
- Task dependencies


## Cytoscape.js

Used for:

- Large graph visualization
- Complex relationships


## ElkJS / Dagre

Used for:

- Automatic graph layouts

---

# 12. Storage Architecture

The system uses graph and vector databases together.

```text
              Knowledge System


                    |

        +-----------+-----------+

        |                       |

 Vector Database          Graph Database

    Milvus                   Neo4j

        |                       |

 Embeddings              Relationships


                    |

             Metadata Database

              PostgreSQL
```

---

# 13. Graph Database Model

Example:

## Concept Node

```json
{
  "type": "concept",
  "name": "Capacitance",
  "subject": "Physics"
}
```

## Relationship

```json
{
  "source": "Capacitance",
  "relation": "requires",
  "target": "Electric Field"
}
```

## User State

```json
{
  "user_id": "abdullah",
  "concept": "Capacitance",
  "confidence": 0.45,
  "status": "needs_revision"
}
```

---

# 14. AI Agent Integration

Different agents use the knowledge graph.

## Tutor Agent

Uses:

- Concept relationships
- Prerequisites
- Related examples


## Planner Agent

Uses:

- Learning dependencies
- Missing concepts
- Goal paths


## Quiz Agent

Uses:

- Weak concepts
- Connected topics


## Revision Agent

Uses:

- Concept confidence
- Forgetting patterns

---

# 15. Future Improvements

Possible extensions:

- Automatic syllabus graph generation
- Cross-subject knowledge connections
- Graph-based reasoning
- AI-generated concept maps
- Learning difficulty prediction
- Community knowledge graphs

---

# 16. Design Goals

The knowledge graph should provide:

- Structured knowledge representation
- Intelligent recommendations
- Adaptive learning paths
- Explainable AI decisions
- Concept dependency reasoning
- Personalized education

The knowledge graph transforms the platform from a document search system into a true learning intelligence system.