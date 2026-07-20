# User & Profile Model

---

# Introduction

The AI Learning Operating System (AI-LOS) is designed around the concept that a single user often studies for multiple goals simultaneously. A learner may be preparing for school examinations, competitive exams, university coursework, certifications, and technical interviews, each requiring separate notes, documents, memories, planners, and progress tracking.

Instead of treating a user as having a single collection of documents, the platform introduces **learning profiles**, allowing every educational goal to exist as an independent workspace while still contributing to a unified learning experience.

---

# Why Profiles?

Traditional note-taking and RAG systems place every document into a single knowledge base.

```
User

├── Physics.pdf
├── Resume.docx
├── Python Notes.md
├── NCERT Biology.pdf
└── Interview Questions.md
```

As the document collection grows, retrieval quality decreases because unrelated materials compete during search.

For example, a question about **Electrostatics** should not retrieve interview notes on CUDA programming.

The platform therefore isolates knowledge into dedicated profiles.

---

# User Hierarchy

The highest level of the system is the **User**.

A user may own multiple learning profiles.

```
User
│
├── Class 10
│
├── Class 12
│
├── JEE
│
├── GATE
│
├── Interview Preparation
│
└── Personal Learning
```

Each profile behaves as an independent educational environment.

---

# Profile Structure

Every profile contains its own resources.

```
Profile
│
├── Subjects
│
├── Documents
│
├── Notes
│
├── Flashcards
│
├── Planner
│
├── Progress
│
├── AI Memory
│
├── Knowledge Graph
│
├── Conversations
│
└── Analytics
```

No information leaks across profiles unless explicitly shared.

---

# Subject Hierarchy

Within each profile, learning is organized into subjects.

Example:

```
Class 12

├── Physics
│
├── Chemistry
│
├── Mathematics
│
└── English
```

Each subject maintains its own educational resources.

---

# Chapter Organization

Subjects are further divided into chapters.

```
Physics

├── Electrostatics

├── Current Electricity

├── Magnetism

├── Optics

└── Modern Physics
```

This hierarchy enables highly accurate metadata filtering during retrieval.

---

# Concept-Level Organization

Each chapter is decomposed into concepts.

```
Current Electricity

├── Ohm's Law

├── Drift Velocity

├── Resistivity

├── Kirchhoff's Laws

└── Wheatstone Bridge
```

The concept level forms the foundation of the knowledge graph.

---

# Complete Learning Hierarchy

```
User
│
└── Profile
     │
     ├── Subject
     │
     ├── Chapter
     │
     ├── Concept
     │
     ├── Documents
     │
     ├── Notes
     │
     ├── Flashcards
     │
     ├── Planner
     │
     ├── AI Memory
     │
     ├── Progress
     │
     └── Analytics
```

---

# Profile Metadata

Each profile stores metadata describing its educational context.

Example:

```json
{
  "profile_id": "class12",
  "name": "Class 12 Boards",
  "exam": "CBSE",
  "target_date": "2027-03-01",
  "daily_study_hours": 4,
  "language": "English",
  "timezone": "Asia/Kolkata"
}
```

Additional fields may include:

- curriculum
- preferred AI model
- revision strategy
- reminder preferences
- grading system

---

# Subject Metadata

Subjects also maintain metadata.

Example:

```json
{
  "subject": "Physics",
  "teacher": "Self Study",
  "difficulty": "Medium",
  "priority": 5,
  "estimated_completion": "2027-02-15"
}
```

---

# Document Ownership

Every uploaded resource belongs to exactly one profile.

```
User

↓

Profile

↓

Subject

↓

Document
```

This guarantees retrieval isolation.

---

# Identity-Based Retrieval

Identity-based retrieval is one of the most important architectural decisions in the platform.

Instead of searching the entire vector database, retrieval automatically filters using profile metadata.

Example metadata stored alongside every embedding:

```json
{
    "user_id": "abdullah",
    "profile_id": "class12",
    "subject": "Physics",
    "chapter": "Electrostatics",
    "difficulty": "Medium",
    "source": "NCERT"
}
```

During retrieval:

```
Current User

↓

Current Profile

↓

Current Subject

↓

Metadata Filter

↓

Vector Search

↓

Relevant Results
```

This dramatically improves retrieval precision while reducing irrelevant context.

---

# Shared Global Planner

Although profiles remain isolated, the user maintains a unified planner.

```
User
│
├── Global Calendar
│
├── Today's Tasks
│
├── Weekly Schedule
│
├── Deadlines
│
└── Notifications
```

Tasks from every profile contribute to the global schedule.

Example:

```
Today

09:00 Physics Revision

11:00 Interview Practice

15:00 Chemistry Quiz

18:00 CUDA Notes
```

---

# Shared Notifications

Notifications are centralized across profiles.

Examples include:

- revision reminders
- planner updates
- upcoming exams
- assignment deadlines
- flashcard reviews

---

# AI Memory Isolation

Long-term AI memory is stored separately for every profile.

```
User
│
├── Class 10 Memory
│
├── Class 12 Memory
│
├── Interview Memory
│
└── Personal Memory
```

This prevents unrelated educational experiences from influencing AI responses.

---

# Progress Tracking

Each profile maintains independent analytics.

Metrics include:

- chapters completed
- study hours
- quiz accuracy
- mastery
- confidence
- retention
- revision count
- streaks

The global dashboard aggregates these metrics without mixing profile knowledge.

---

# Permissions

Profiles may optionally be shared.

Supported roles include:

| Role        | Permissions                |
| ----------- | -------------------------- |
| Owner       | Full control               |
| Editor      | Modify documents and notes |
| Contributor | Add resources              |
| Viewer      | Read-only access           |

This enables collaborative classrooms and study groups.

---

# Profile Lifecycle

A profile follows the lifecycle below.

```
Create Profile

↓

Configure Subjects

↓

Upload Resources

↓

Generate Embeddings

↓

Study

↓

Track Progress

↓

Revise

↓

Complete Goals

↓

Archive
```

Archived profiles remain searchable but no longer receive planner updates.

---

# Benefits of the Profile Model

The profile architecture provides several advantages.

- Personalized retrieval
- Cleaner vector search
- Independent AI memory
- Subject-specific analytics
- Adaptive planners
- Separate revision schedules
- Better scalability
- Reduced retrieval noise
- Easier collaboration
- Improved maintainability

---

# Future Extensions

Future versions may support:

- institution-managed profiles
- teacher-created profiles
- organization workspaces
- family accounts
- shared classrooms
- certification pathways
- enterprise learning profiles
- profile templates

---

# Summary

The User & Profile Model provides the organizational backbone of the AI Learning Operating System. By introducing profile-level isolation, subject hierarchies, metadata-driven retrieval, independent AI memory, and unified planning, the platform supports multiple concurrent learning goals while maintaining highly personalized, scalable, and context-aware educational experiences.