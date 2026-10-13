# Containerized Compiler Testbench with LLM-Driven Triage

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ephemeral%20sandboxes-2496ED.svg)](https://www.docker.com/)
[![GCC 13](https://img.shields.io/badge/gcc-13%20(C%2B%2B20)-green.svg)](https://gcc.gnu.org/)
[![Clang 18](https://img.shields.io/badge/clang-18%20(LLVM)-red.svg)](https://clang.llvm.org/)
[![Vector DB](https://img.shields.io/badge/Pinecone-Serverless%20RAG-000000.svg)](https://www.pinecone.io/)
[![Multi-LLM](https://img.shields.io/badge/AI%20Triage-Gemini%20%7C%20Groq%20%7C%20Grok-8A2BE2.svg)](https://ai.google.dev/)
[![Redis](https://img.shields.io/badge/cache-Redis%20Online-DC382D.svg)](https://redis.io/)

An automated compiler stress testing and automated root-cause triage platform. This testbench dynamically generates syntactically valid yet structurally tortuous C++20 code, executes compilations inside isolated ephemeral Docker containers under strict resource quotas, detects Internal Compiler Errors (ICEs) or compilation failures, and dispatches compiler diagnostic dumps to a **Pinecone Vector RAG** and a **Multi-Model Fallback AI Triage Engine**.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph GEN ["1. Test Generation Engine"]
        A["Synthetic C++20 Test Generator<br/>(12 Complex Stress & Edge Categories)"]
    end

    subgraph SANDBOX ["2. Isolated Ephemeral Docker Sandboxes"]
        direction TB
        B1["GCC 13 Sandbox<br/>(Ubuntu 24.04)"]
        B2["Clang 18 Sandbox<br/>(Ubuntu 24.04 / LLVM)"]
        LIMITS["cgroups Security Quotas:<br/>• 512MB RAM Limit<br/>• 50% CPU Quota<br/>• Network Mode: none<br/>• Non-root User Isolation"]
    end

    subgraph EVAL ["3. Result Evaluation & Caching"]
        D{"Compilation Status"}
        PASS["Record Latency & Summary<br/>(Exit Code 0)"]
        CACHE[("Redis Triage Cache<br/>SHA-256 Log Digest")]
    end

    subgraph RAG_LAYER ["4. Pinecone Vector RAG"]
        VEC[("Pinecone Serverless Index<br/>compiler-crashes (768-dim)")]
        CORPUS[("Historical Bug Corpus<br/>GCC & LLVM ICE Signatures")]
    end

    subgraph AI_TRIAGE ["5. Multi-Model Fallback AI Triage"]
        LLM1["Primary: Google Gemini 2.5 Flash"]
        LLM2["Secondary: Groq Cloud / xAI Grok"]
        LLM3["Tertiary: Local Heuristic Compiler Engine"]
    end

    subgraph DASHBOARD ["6. Real-Time Diagnostics & Reporting"]
        CLI["Rich Terminal Dashboard<br/>• Diagnostic Classification<br/>• Root Cause Analysis<br/>• Mitigation & Workaround Flags<br/>• Cross-Compiler Differential Table"]
    end

    A --> B1
    A --> B2
    LIMITS -.- B1
    LIMITS -.- B2

    B1 --> D
    B2 --> D

    D -- "PASS (Exit 0)" --> PASS
    D -- "COMPILE_ERROR / CRASH / ICE" --> CACHE

    CACHE -- "Cache Hit (<2ms)" --> CLI
    CACHE -- "Cache Miss" --> VEC
    CORPUS -. "Seed Data" .-> VEC

    VEC -- "Top-K Similar Historical Bugs" --> LLM1
    LLM1 -- "Success" --> CLI
    LLM1 -- "Rate Limit / Failure" --> LLM2
    LLM2 -- "Success" --> CLI
    LLM2 -- "Network / API Exhaustion" --> LLM3
    LLM3 --> CLI
    PASS --> CLI
```

---

## Key Features

- **Isolated Docker Sandboxing**: Compilations execute strictly inside disposable containers with non-root security privileges, `network_mode="none"`, memory limits (`512MB`), and CPU quotas (`0.5 cores`). The host operating system remains untouched.
- **Dual-Compiler Differential Testing**: Run the exact same C++ code simultaneously across **GCC 13** and **Clang 18** to pinpoint compiler divergences, non-standard behaviors, and internal bugs.
- **Dynamic C++20 Stress Generator**: Emits complex test suites across 6 stress categories (12 specific tests):
  1. Deep Template Metaprogramming & recursive SFINAE
  2. Pointer Aliasing, Multi-dimensional Offsets & Strict Aliasing Barriers
  3. Inline Assembly & Machine Register Allocator Contention
  4. Concurrency, Atomic Memory Orderings & Sequential Consistency
  5. Tree-SSA Loop Auto-Vectorizer & SIMD unrolling limits
  6. C++20 Concepts, cyclic constraints & deep generic inlining closures
- **Pinecone Vector RAG**: Embeds compiler error logs into 768-dimensional space to query a historical corpus of real-world GCC and LLVM Internal Compiler Errors (ICEs), matching stack traces to verified bug IDs (e.g., `LLVM-61204`, `GCC-98512`).
- **Resilient Multi-Model Fallback Chain**:
  1. **Primary**: Google Gemini (`gemini-2.5-flash`)
  2. **Secondary**: Groq Cloud (`qwen/qwen3.8-27b`) or xAI Grok (`grok-2-latest`) via automatic key detection
  3. **Tertiary**: Local deterministic heuristic compiler triage engine (operates completely offline if network/APIs are exhausted)
- **Redis Triage Caching**: Identical compilation failures and crash signatures are hashed (SHA-256) and served from Redis in `< 2ms`, preventing duplicate API invocations and cost.
- **Rich Terminal UI**: Live telemetry, formatted Markdown diagnostic reports, and comprehensive pass/fail summary tables.

---

## Directory Structure

```
.
├── .env.example                     # Environment template
├── Dockerfile.gcc                   # GCC 13 sandbox container specification
├── Dockerfile.clang                 # Clang 18 / LLVM sandbox container specification
├── main.py                          # Unified CLI entry point & orchestrator
├── requirements.txt                 # Python project dependencies
├── data/
│   └── historical_bugs.json         # Seed corpus of real-world GCC & LLVM ICE bugs
├── docker/
│   ├── Dockerfile.gcc
│   └── Dockerfile.clang
├── src/
│   ├── engine/
│   │   ├── generator.py             # Synthetic C++20 stress code generator
│   │   └── runner.py                # Ephemeral Docker container compilation runner
│   ├── llm/
│   │   └── triage_agent.py          # Multi-LLM fallback chain (Gemini -> Groq/Grok -> Local)
│   ├── rag/
│   │   └── vector_store.py          # Pinecone serverless vector database integration
│   └── utils/
│       └── cache.py                 # Redis triage report caching layer
└── tests/
    ├── test_generator.py            # Unit tests for test generator logic
    ├── test_sandbox_runner.py       # Integration tests for Docker sandbox isolation
    └── verify_all_tests.py          # Full matrix validation across all 12 stress cases
```

---

## Prerequisites

1. **Docker Desktop**: Must be installed and running.
2. **Python**: Version 3.10 or higher.
3. **API Keys** (Optional but recommended for full RAG & AI triage):
   - [Pinecone API Key](https://www.pinecone.io/) (for historical bug vector retrieval)
   - [Google AI Studio API Key](https://aistudio.google.com/) (for Gemini Flash)
   - [Groq Cloud API Key](https://console.groq.com/) or [xAI Console Key](https://console.x.ai/) (for fallback triage)

---

## Installation & Setup

### 1. Clone the Repository & Setup Python Environment

```bash
git clone <repo-url>
cd "Containerized Compiler Testbench with LLM-Driven Triage"

# Create and activate virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example configuration to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```ini
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=compiler-crashes
GEMINI_API_KEY=your_gemini_api_key_here
GROK_API_KEY=your_groq_or_grok_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
```

> **Note**: If `GROK_API_KEY` starts with `gsk_`, the runner automatically routes requests to **Groq Cloud** using fast Qwen/Llama models. If it starts with `xai-`, it automatically routes to **xAI Grok**.

### 3. Build Docker Sandbox Containers

Build the ephemeral compilation environments:

```bash
# Build GCC 13 Sandbox
docker build -t compiler-sandbox-gcc:latest -f docker/Dockerfile.gcc .

# Build Clang 18 Sandbox
docker build -t compiler-sandbox-clang:latest -f docker/Dockerfile.clang .
```

### 4. Start Redis Container (For Triage Caching)

```bash
docker run -d --name compiler-redis -p 6379:6379 redis:alpine
```

---

## Usage Guide

### Seed the Pinecone Vector Database
Ingest the historical compiler crash corpus (`data/historical_bugs.json`) into your Pinecone serverless vector index:

```bash
python main.py --seed-db
```

### Run Default Testbench (GCC)
Generate 4 balanced tests and execute inside the GCC container:

```bash
python main.py
```

### Run Differential Testing (GCC vs. Clang)
Execute compilations side-by-side on both compilers to detect compiler-specific divergences:

```bash
python main.py --compiler both --count 4
```

### Target Clang Exclusively
```bash
python main.py --compiler clang --count 4
```

### Choose Stress Mode
- `--mode balanced` (Default): Mix of valid complex codes and edge-case limit tests.
- `--mode aggressive`: Targets severe compiler stress and edge-case failure boundaries.
- `--mode valid-only`: Verifies that complex valid programs compile cleanly without syntax errors.

```bash
python main.py --mode aggressive --count 6
```

### Live Container Telemetry Mode
Stream container execution duration and real-time logs to the console:

```bash
python main.py --live --count 4
```

### Inject Deliberate ICE / Syntax Stress
Inject an extreme SFINAE template recursion file to explicitly verify the AI triage loop:

```bash
python main.py --inject-broken
```

---

## CLI Options Reference

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--count` | `int` | `4` | Number of synthetic C++ tests to generate |
| `--mode` | `str` | `balanced` | Stress mode: `balanced`, `aggressive`, or `valid-only` |
| `--compiler` | `str` | `gcc` | Target sandbox: `gcc`, `clang`, or `both` |
| `--seed-db` | `flag` | `False` | Seeds `data/historical_bugs.json` into Pinecone vector store |
| `--live` | `flag` | `False` | Prints real-time container run telemetry and timing |
| `--output-dir`| `str` | `compiler_tests` | Directory to store generated test source files |
| `--inject-broken` | `flag` | `False` | Injects an intentional template recursion crash test |

---

## Verification & Automated Tests

Run the test suite to verify the generator and Docker runner:

```bash
# Verify all 12 synthetic C++ stress cases inside GCC container
python tests/verify_all_tests.py

# Run unit tests via pytest
pytest tests/ -v
```

All 12 generator test cases are verified to produce 100% deterministic expected outcomes (valid tests cleanly exit `0`, and limit stress cases cleanly emit their targeted compiler diagnostics).

---

## System Engineering Highlights

### 1. Why Ephemeral Docker Sandboxes for Compiler Testing?
- **Security & Blast Radius Isolation**: Complex C++ code featuring inline assembly, memory layout manipulation, or preprocessor expansions can trigger resource exhaustion, host segfaults, or compiler vulnerabilities.
- **Resource Containment**: With `--memory=512m` and `cpu_quota=50000`, runaway template recursions or exponential inlining cannot freeze or starve the host system.
- **Network Isolation**: Running with `network_mode="none"` prevents untrusted compilation scripts from initiating outbound network calls.

### 2. Why Differential Testing (GCC vs. Clang)?
- C++ standard specifications (ISO/IEC 14882) are written in natural language. Compiling the exact same program through both independent compiler codebases reveals:
  - Divergences in standards interpretation (e.g., C++20 Concepts constraint ordering).
  - Optimizer bugs where one compiler emits bad machine code or crashes while the other succeeds.
  - Undefined Behavior (UB) exploitation differences.

### 3. RAG-Driven Compiler Triage
- Compiler error logs and Internal Compiler Error (ICE) dumps are notoriously verbose.
- By converting error signatures into vector embeddings and performing cosine similarity lookups against known bug databases (e.g., LLVM Bugzilla, GCC Bug Tracker), the LLM is supplied with **ground-truth context**, eliminating hallucinations and outputting actionable mitigation flags in milliseconds.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
