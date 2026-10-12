# Project Workflow: Containerized Compiler Testbench with LLM-Driven Triage

This document tracks the phased implementation and operational workflow for the Containerized Compiler Testbench with LLM-Driven Triage.

## Architecture Overview
1. **Engine Layer (`src/engine`)**:
   - `generator.py`: Generates synthetic stress-testing C++ source codes (deep metaprogramming recursion, complex aliasing, volatile/inline asm, concurrency edge cases).
   - `runner.py`: Orchestrates isolated compilation in ephemeral Docker containers under strict quotas (`mem_limit="512m"`, `cpu_quota=50000`, `network_mode="none"`).
2. **RAG & Knowledge Layer (`src/rag`)**:
   - `vector_store.py`: Pinecone vector store client for historical compiler ICEs (Internal Compiler Errors), segfaults, and bug tracker signatures.
   - `data/historical_bugs.json`: Canonical dataset of historical GCC/Clang crash signatures.
3. **LLM Triage Layer (`src/llm`)**:
   - `triage_agent.py`: Multi-model fallback chain (Gemini with fallback handling) generating structured triage reports (root cause, bug category, patch/workaround recommendations).
4. **Utilities & CLI (`src/utils`, `main.py`)**:
   - Redis caching for query embeddings and previous triage outputs.
   - Rich CLI logging and execution dashboard.

---

## Phased Roadmap & Execution Checklist

- [x] **Phase 1: Environment & Test Case Generation**
  - [x] Initialize project skeleton (`docker/`, `src/engine/`, `src/rag/`, `src/llm/`, `src/utils/`, `compiler_tests/`, `data/`).
  - [x] Configure environment variables (`.env`, `.env.example`, `requirements.txt`).
  - [x] Implement `CompilerTestGenerator` in `src/engine/generator.py` targeting template recursion, pointer aliasing, inline asm/volatile, and concurrency uninitialized memory.
  - [x] Verification: Test generator suite generation and validate C++ syntax.

- [x] **Phase 2: Isolated Container Sandbox Runner**
  - [x] Dockerfile definition (`docker/Dockerfile.gcc` and `docker/Dockerfile.clang`).
  - [x] Build `CompilerSandbox` in `src/engine/runner.py` with resource quotas and guaranteed cleanup (`finally` block).
  - [x] Standardized payload generation (`PASS`, `COMPILE_ERROR`, `CRASH`).
  - [x] Verification: Test with known clean and broken snippets; verify zero orphaned containers.

- [x] **Phase 3: Pinecone Vector Database & Knowledge Ingestion**
  - [x] Curate 12 realistic GCC/Clang crash logs and metadata in `data/historical_bugs.json`.
  - [x] Implement Pinecone client, indexing, embedding, and cosine similarity query in `src/rag/vector_store.py`.
  - [x] Implement graceful offline/mock fallback for when Pinecone credentials are not configured or network is isolated.
  - [x] Verification: Ingest seed data and test query with sample crash log.

- [x] **Phase 4: LLM Triage & Fallback Chains**
  - [x] Implement `src/llm/triage_agent.py` with multi-model fallback chain and structured output parser.
  - [x] Verification: Mock crash dump and mock vector context triage test.

- [x] **Phase 5: Unified Pipeline & CLI Dashboard**
  - [x] Implement `main.py` CLI (`--count`, `--seed-db`, `--live`, `--inject-broken`).
  - [x] End-to-end integration test executed with 5 generated tests, live container execution, RAG matching, and triage dashboard.
