# AI Learning Operating System
## 04 - Data Model & Domain Architecture

---

# Overview

This document defines the complete domain model of the AI Learning Operating System.

The goal is to build a strongly connected knowledge ecosystem rather than isolated tables.

Every object should be uniquely identifiable, searchable, versioned, and linked to other entities.

The domain model should support

- personalized retrieval
- multi-profile learning
- AI memory
- planner generation
- collaborative editing
- analytics
- future scalability

---

# Core Entity Hierarchy

```
Organization (future)

↓

User

↓

Profile

↓

Subject

↓

Chapter

↓

Learning Assets

↓

Knowledge Objects

↓

Analytics
```

---

# User

The User represents a human account.

One user may own multiple independent learning profiles.

Example

```
Abdullah

├── Class 12

├── JEE

├── FPGA Research

├── CUDA

└── Interview Preparation
```

---

## User Fields

```
User

id

email

username

display_name

profile_picture

timezone

language

theme

preferred_llm

subscription

created_at

updated_at
```

---

# User Relationships

```
User

├── Profiles

├── Global Calendar

├── Notifications

├── AI Preferences

├── Global Planner

├── Global Memory

└── Settings
```

---

# Learning Profile

Profiles isolate learning environments.

Nothing from one profile should affect another unless explicitly shared.

Examples

```
Class 10

Class 12

UPSC

GATE

Research

Interview
```

---

## Profile Fields

```
Profile

id

user_id

name

description

exam

board

target_date

preferred_language

difficulty

status
```

---

# Profile Relationships

```
Profile

├── Subjects

├── Documents

├── Notes

├── Flashcards

├── Quizzes

├── Planner

├── AI Memory

├── Progress

├── Knowledge Graph

└── Analytics
```

---

# Subject

Subjects organize knowledge.

```
Physics

Chemistry

Mathematics

English

CUDA

FPGA
```

---

## Subject Fields

```
Subject

id

profile_id

name

description

icon

color

difficulty

progress
```

---

# Chapter

Subjects contain chapters.

```
Physics

├── Electrostatics

├── Magnetism

├── Current Electricity

├── Optics
```

---

## Chapter Fields

```
Chapter

id

subject_id

title

description

order

difficulty

estimated_hours

confidence

mastery

completion
```

---

# Learning Assets

Learning assets are user-created or uploaded content.

```
Documents

Notes

Whiteboards

Code

Images

Videos

Audio

Bookmarks
```

Every asset should support

- search
- embeddings
- AI annotations
- version history
- collaboration

---

# Document

Supported

PDF

DOCX

Markdown

TXT

PowerPoint

Excel

Image

Audio

Video

---

## Document Fields

```
Document

id

profile_id

subject_id

chapter_id

title

type

mime_type

storage_path

size

checksum

created_at

updated_at

metadata
```

---

# Note

Notes may originate from

manual writing

AI generation

PDF highlights

DOCX selections

meeting notes

voice transcription

---

## Note Fields

```
Note

id

document_id

profile_id

title

markdown

frontmatter

tags

version

created_at

updated_at
```

---

# Chunk

Chunks are the smallest retrievable units.

Every chunk belongs to exactly one source.

```
Chunk

↓

Embedding

↓

Metadata

↓

Search

↓

Citation
```

---

## Chunk Fields

```
Chunk

id

document_id

chunk_index

text

tokens

embedding_id

metadata

page_number

section

heading
```

---

# Embedding

Embeddings should never exist without metadata.

```
Embedding

id

chunk_id

model

dimensions

vector

created_at
```

---

# Metadata

Every searchable object includes metadata.

Example

```json
{
  "user_id":"...",
  "profile_id":"class12",
  "subject":"Physics",
  "chapter":"Electrostatics",
  "source":"NCERT",
  "difficulty":"Medium",
  "tags":["electricity","capacitor"]
}
```

Metadata enables

- filtering
- retrieval
- analytics
- planner generation

---

# Conversation

Every AI interaction is stored.

```
Conversation

↓

Messages

↓

Retrieved Context

↓

Tools

↓

Memory Updates
```

---

## Conversation Fields

```
Conversation

id

profile_id

title

model

started_at

updated_at
```

---

# Message

```
Message

id

conversation_id

role

content

tool_calls

citations

token_usage

latency

timestamp
```

---

# AI Memory

Memory stores persistent learner information.

Categories

```
Preferences

↓

Weak Concepts

↓

Strong Concepts

↓

Learning Style

↓

Writing Style

↓

Goals

↓

Planner History

↓

Conversation Summary
```

---

## Memory Fields

```
Memory

id

profile_id

category

importance

content

confidence

last_accessed

created_at
```

---

# Planner

The planner is hierarchical.

```
Goal

↓

Milestone

↓

Subject

↓

Chapter

↓

Task
```

---

## Planner Fields

```
Task

id

profile_id

parent_task

title

description

priority

deadline

estimated_time

status

progress
```

---

# Flashcard

```
Flashcard

id

profile_id

front

back

difficulty

source

created_at
```

---

# FSRS State

Each flashcard stores scheduling state.

```
Review

↓

Difficulty

↓

Stability

↓

Next Review

↓

Interval
```

---

# Quiz

```
Quiz

id

profile_id

title

difficulty

chapter

generated_by

created_at
```

---

# Question

```
Question

id

quiz_id

type

prompt

options

answer

explanation

difficulty
```

---

# Progress

Progress should exist at every hierarchy.

```
User

↓

Profile

↓

Subject

↓

Chapter

↓

Task

↓

Flashcard
```

---

## Metrics

Track

- mastery
- confidence
- revision count
- accuracy
- study hours
- streak
- retention
- Bloom level
- interview readiness

---

# Knowledge Graph

Everything becomes a graph.

```
Concept

↓

depends_on

↓

Concept

↓

explained_by

↓

Document

↓

summarized_by

↓

Note

↓

tested_by

↓

Quiz

↓

reinforced_by

↓

Flashcard
```

---

# Graph Node Types

```
User

Profile

Subject

Chapter

Concept

Document

Chunk

Note

Conversation

Task

Quiz

Flashcard
```

---

# Graph Edge Types

```
depends_on

related_to

references

generated_from

mentions

belongs_to

recommended_before

recommended_after

summarizes

explains

derived_from
```

---

# Event Model

Every entity produces events.

Examples

```
DocumentUploaded

DocumentParsed

EmbeddingCreated

GraphUpdated

MemoryUpdated

PlannerUpdated

QuizCompleted

RevisionCompleted

TaskFinished

FlashcardReviewed
```

No service should directly modify another service's data.

Everything should react to events.

---

# Versioning

Every editable entity supports

```
Version 1

↓

Version 2

↓

Version 3

↓

Restore
```

Applicable to

- notes
- documents
- planners
- quizzes
- flashcards

---

# Ownership Rules

Every object belongs to exactly one profile.

```
User

↓

Profile

↓

Everything Else
```

This guarantees strict identity-based retrieval and complete isolation between learning environments.

---

# Data Lifecycle

```
Upload

↓

Parse

↓

Chunk

↓

Embed

↓

Retrieve

↓

Answer

↓

Memory Update

↓

Planner Update

↓

Progress Update

↓

Analytics

↓

Archive
```

---

# Design Principles

The domain model should satisfy the following principles.

✓ Identity-aware

✓ Profile-aware

✓ Event-driven

✓ Versioned

✓ Searchable

✓ AI-native

✓ Graph-connected

✓ Retrieval-friendly

✓ Analytics-ready

✓ Extensible

Every future feature should be representable by extending the domain model rather than redesigning it.