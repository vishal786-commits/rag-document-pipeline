# RAG Document Pipeline

A modular **Retrieval-Augmented Generation (RAG)** system built from scratch in Python.  
This project demonstrates a complete pipeline for transforming documents into a searchable knowledge base and answering questions using semantic retrieval and large language models.

The system ingests a document, splits it into meaningful chunks, generates embeddings, stores them in a vector database, and retrieves relevant context to generate accurate answers.

---

## Overview

Large Language Models are powerful but lack access to external knowledge unless it is provided during inference.  

**Retrieval-Augmented Generation (RAG)** solves this by retrieving relevant information from a document corpus and injecting it into the prompt before generation.

This project implements a **minimal, modular RAG architecture** that can serve as the foundation for production document QA systems.

Example use case implemented in this repository:  
Indexing and querying *The Problem of the Puer Aeternus*.

---

## System Architecture

<p align="center">
  <img src="assets/System%20Architecture.png" alt="RAG System Architecture" width="800"/>
</p>

Pipeline flow:

1. Extract text from a PDF  
2. Split text into overlapping chunks  
3. Generate vector embeddings  
4. Store vectors in Pinecone  
5. Convert user query into an embedding  
6. Retrieve relevant chunks  
7. Generate an answer using an LLM  

---

## Project Structure

```
rag-document-pipeline
│
├── data
│   └── The Problem of the Puer Aeternus.pdf
│
├── src
│   ├── chunker.py
│   ├── embedder.py
│   ├── pdfreader.py
│   ├── vectorstore.py
│   └── llm.py
│
├── ingest.py
├── query.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## Module Responsibilities

| Module | Description |
|------|-------------|
| `pdfreader.py` | Extracts raw text from PDF documents |
| `chunker.py` | Splits documents into overlapping chunks |
| `embedder.py` | Generates embeddings for text chunks |
| `vectorstore.py` | Stores and retrieves embeddings from Pinecone |
| `query.py` | Handles query processing and retrieval |
| `llm.py` | Sends context and queries to the language model |
| `ingest.py` | Runs the document ingestion pipeline |

---

## Future Improvements

- Add **FastAPI service layer** for API access  
- Implement **hybrid retrieval (BM25 + embeddings)**  
- Add **cross-encoder reranking**  
- Support **multiple document collections**  
- Add **metadata filtering**  
- Implement **evaluation metrics for retrieval quality**  
- Containerize deployment with **Docker**  
- Add **streaming LLM responses**

---

## Learning Objectives

This project focuses on understanding the **core components of modern retrieval systems** rather than relying on high-level frameworks.

Key concepts demonstrated:

- vector embeddings  
- semantic search  
- retrieval pipelines  
- prompt grounding  
- modular AI system design  

---

## License

*To be declared*
