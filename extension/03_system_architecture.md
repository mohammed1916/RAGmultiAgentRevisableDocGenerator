# AI Learning Operating System
## 03 - System Architecture Specification

---

# Overview

This document defines the complete system architecture of the AI Learning Operating System.

The architecture follows a modular, event-driven microservice design where every subsystem has a well-defined responsibility and communicates through APIs and events rather than direct coupling.

The primary design goals are

- scalability
- modularity
- extensibility
- maintainability
- observability
- replaceable AI components

No service should directly depend on the implementation details of another service.

---

# High-Level Architecture

```
                          Client Applications
┌────────────────────────────────────────────────────────────┐
│ React Web │ Mobile │ Desktop │ Obsidian Plugin │ API Client │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    API Gateway / Backend
                            │
────────────────────────────────────────────────────────────────
                            │
    ┌──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼
Authentication   Workspace     AI Gateway
Service          Service
    │              │              │
    ▼              ▼              ▼
Planner      Retrieval      Agent Orchestrator
Service      Service
    │              │              │
    ▼              ▼              ▼
Memory      Knowledge      Analytics
Service      Graph
    │              │              │
    ▼              ▼              ▼
Notification Worker Services Event Bus
```

---

# Core Principles

Every subsystem must satisfy

- Single Responsibility
- Independent Deployment
- API-first
- Event-driven synchronization
- Stateless services where possible
- Replaceable implementations

---

# System Layers

```
Presentation Layer

↓

Application Layer

↓

AI Layer

↓

Knowledge Layer

↓

Storage Layer

↓

Infrastructure Layer
```

---

# Presentation Layer

Purpose

Provide interfaces for users.

Supported clients

- Web Application
- Mobile Application
- Desktop Application
- Obsidian Plugin
- Public REST API
- Future CLI

Responsibilities

- rendering UI
- authentication
- routing
- caching
- optimistic updates
- websocket communication

---

# Application Layer

Contains business logic.

Modules

Workspace

Planner

Progress

Flashcards

Quiz

Collaboration

Notifications

Settings

Authentication

No AI logic exists here.

---

# AI Layer

Responsible for all AI interactions.

Components

```
AI Gateway

↓

Context Builder

↓

Tool Calling

↓

Agent Orchestrator

↓

LLM Provider
```

Responsibilities

- prompt construction
- tool routing
- model selection
- structured outputs
- streaming responses
- retry logic

The application should never directly call the LLM.

Everything goes through the AI Gateway.

---

# Knowledge Layer

Contains

- retrieval
- embeddings
- reranking
- graph
- memory

Responsible for producing high-quality context.

```
Question

↓

Metadata Filter

↓

Hybrid Search

↓

Memory Retrieval

↓

Knowledge Graph

↓

Planner

↓

Context Compression

↓

LLM
```

---

# Storage Layer

Responsible for persistence.

Stores

Structured Data

↓

Documents

↓

Embeddings

↓

Graphs

↓

Caches

↓

Analytics

↓

Memory

Different storage systems should be optimized for different workloads.

---

# Infrastructure Layer

Contains

- Docker
- Kubernetes (future)
- Redis
- Message Queue
- Monitoring
- Logging

No application logic belongs here.

---

# Major Services

---

# Authentication Service

Responsibilities

- registration
- login
- OAuth
- JWT
- sessions
- RBAC
- permissions

Suggested technologies

- Better Auth
- Auth.js
- Clerk
- Supabase Auth

---

# Workspace Service

Handles

Markdown

DOCX

PDF

Images

Code

Whiteboards

Responsibilities

- open
- edit
- autosave
- version history
- synchronization

---

# Document Service

Responsible for

upload

download

delete

metadata

folder organization

versioning

storage

Supported storage

- S3
- Cloudflare R2
- Azure Blob
- Supabase Storage

---

# Ingestion Service

Automatically processes uploaded documents.

Pipeline

```
Upload

↓

Detect File Type

↓

OCR

↓

Extract Text

↓

Clean

↓

Chunk

↓

Metadata

↓

Embeddings

↓

Store

↓

Knowledge Graph
```

Supported formats

PDF

DOCX

Markdown

PowerPoint

Excel

Images

Audio

Video

---

# Retrieval Service

Purpose

Retrieve the most relevant knowledge.

Pipeline

```
Question

↓

Metadata Filter

↓

BM25

↓

Vector Search

↓

Merge

↓

Reranker

↓

Context Compression

↓

Return Context
```

Supports

- semantic search
- keyword search
- hybrid search
- metadata filtering

---

# Memory Service

Purpose

Store long-term learning memory.

Memory types

Conversation

↓

Preference

↓

Weak Topic

↓

Strong Topic

↓

Learning Style

↓

Study Pattern

↓

Planner History

Memory should evolve continuously.

Suggested framework

Mem0

---

# Knowledge Graph Service

Maintains relationships.

Entities

User

Profile

Subject

Chapter

Concept

Note

Document

Flashcard

Quiz

Task

Edges

depends_on

related_to

explains

generated_from

reviews

references

recommended_before

Supports

- prerequisite detection
- concept exploration
- graph visualization

---

# Planner Service

Generates

daily

weekly

monthly

exam

revision

plans

Inputs

Current progress

↓

Exam date

↓

Available hours

↓

Weak topics

↓

Memory

↓

Planner

↓

Study Plan

---

# Flashcard Service

Responsibilities

- generation
- scheduling
- review
- import
- export

Scheduling

FSRS

Supports

- markdown
- images
- equations

---

# Quiz Service

Question types

MCQ

Coding

Essay

Fill Blank

True False

Generated from

Documents

↓

Notes

↓

Videos

↓

Memory

↓

Knowledge Graph

---

# Progress Service

Tracks

study hours

confidence

accuracy

retention

revision

mastery

Bloom level

completion

---

# Analytics Service

Produces

- dashboards
- reports
- trends
- heatmaps
- predictions

Metrics

Token Usage

Latency

Retrieval Quality

Planner Efficiency

Study Time

Revision Frequency

Memory Growth

---

# Notification Service

Generates

planner reminders

revision reminders

deadline alerts

collaboration notifications

AI recommendations

Supports

Email

Push

SMS (future)

In-app

---

# Collaboration Service

Supports

- shared workspaces
- collaborative editing
- comments
- presence
- cursors

Technology

Yjs

Hocuspocus

---

# AI Gateway

Single entry point to AI.

Responsibilities

Choose Model

↓

Collect Context

↓

Execute Tools

↓

Retry

↓

Return Streaming Response

Supports

- GPT
- local models
- Anthropic
- Gemini
- future providers

---

# Agent Orchestrator

Uses LangGraph.

Agents

Planner

Retriever

Writer

Memory

Revision

Progress

Quiz

Interview

Research

Every agent has

inputs

tools

outputs

state

memory

---

# Event Bus

Every subsystem communicates through events.

Examples

```
Document Uploaded

↓

OCR Completed

↓

Embeddings Created

↓

Graph Updated

↓

Planner Updated

↓

Progress Updated
```

Another example

```
Quiz Completed

↓

Confidence Updated

↓

FSRS Updated

↓

Memory Updated

↓

Dashboard Updated
```

Possible implementations

- Redis Streams
- Kafka
- RabbitMQ
- NATS

---

# Caching Layer

Use Redis.

Cache

Embeddings

Planner

AI Responses

Search Results

User Sessions

Graph Queries

---

# Database Layer

Recommended databases

Relational

PostgreSQL

Vector

Milvus

Cache

Redis

Object Storage

S3 / R2

Graph

Neo4j (optional) or PostgreSQL graph tables

Analytics

ClickHouse (future)

---

# API Design

Prefer

REST

for CRUD

GraphQL

for UI aggregation

WebSockets

for collaboration

SSE

for AI streaming

---

# Security

Implement

JWT

RBAC

Encrypted storage

HTTPS

Rate limiting

Audit logging

Input validation

Prompt injection protection

File scanning

---

# Observability

Every service should expose

Health

Metrics

Logs

Tracing

Recommended stack

Prometheus

Grafana

OpenTelemetry

Loki

---

# Deployment

Development

Docker Compose

Production

Kubernetes

Cloud

Azure

AWS

GCP

Self-hosted

---

# Complete System Flow

```
User

↓

Authentication

↓

Profile Selected

↓

Workspace

↓

Upload / Edit Document

↓

Ingestion Pipeline

↓

Chunking

↓

Embedding

↓

Knowledge Graph

↓

Memory

↓

Planner

↓

Hybrid Retrieval

↓

AI Gateway

↓

Agent Orchestrator

↓

GPT

↓

Streaming Response

↓

Planner Updated

↓

Progress Updated

↓

Memory Updated

↓

Dashboard Updated
```

---

# Architectural Principles Summary

The architecture should remain

✓ Modular

✓ Event Driven

✓ AI First

✓ Retrieval First

✓ Memory Aware

✓ Profile Aware

✓ Extensible

✓ Observable

✓ Replaceable

✓ Cloud Native

✓ Self-hostable

Every component should be independently replaceable without requiring major changes to the remaining system.