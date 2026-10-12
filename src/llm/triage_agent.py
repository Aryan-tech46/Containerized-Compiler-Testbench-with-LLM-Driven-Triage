"""LLM Triage Agent and Fallback Orchestrator module.

Analyzes compiler crashes and internal compiler errors (ICE) using
multi-model fallback chains and retrieved RAG context.
"""

import json
import os
import re
import warnings
from typing import Dict, List, Any, Optional

warnings.filterwarnings("ignore", category=FutureWarning)

from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    genai = None


import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class TriageReport(BaseModel):
    """Structured report schema produced by the compiler triage engine."""
    bug_category: str = Field(
        ...,
        description="Category such as Frontend Parser, Instruction Selection, Loop Optimization, etc."
    )
    historical_match_id: str = Field(
        ...,
        description="Matched Bug ID from historical database, e.g. GCC-98512"
    )
    similarity_confidence: str = Field(
        ...,
        description="Confidence level or similarity score (e.g. HIGH (0.85) or MODERATE (0.55))"
    )
    root_cause_analysis: str = Field(
        ...,
        description="In-depth analysis of why the crash or ICE occurred"
    )
    recommended_mitigation: str = Field(
        ...,
        description="Actionable compiler flag workarounds or AST source patch suggestions"
    )

    def to_markdown(self) -> str:
        """Renders the triage report in clean GitHub Markdown format."""
        return (
            f"### [TRIAGE REPORT] Compiler Crash Analysis\n\n"
            f"- **Bug Category:** `{self.bug_category}`\n"
            f"- **Historical Match:** `{self.historical_match_id}` ({self.similarity_confidence})\n\n"
            f"#### Root Cause Analysis\n"
            f"{self.root_cause_analysis}\n\n"
            f"#### Recommended Mitigation\n"
            f"{self.recommended_mitigation}\n"
        )


SYSTEM_PROMPT = """You are a Principal Compiler Verification and Diagnostics Engineer specializing in GCC and Clang/LLVM internal compiler errors (ICE), optimizer panics, and segmentation faults.

Given:
1. The raw compiler stderr/stdout crash dump.
2. Retrieved candidate historical bugs from the Pinecone vector database with their similarity scores and known root causes.

Analyze the crash log, correlate it with the retrieved historical records, and produce a structured triage report.
You must output strictly valid JSON matching the following schema:
{
    "bug_category": "<category e.g. Frontend Parser / Template Substitution, Instruction Selection, etc.>",
    "historical_match_id": "<Best matching Bug ID e.g. GCC-98512 or None>",
    "similarity_confidence": "<HIGH (>0.7), MEDIUM (0.4-0.7), or LOW (<0.4)>",
    "root_cause_analysis": "<Detailed technical explanation of why the crash or ICE occurred>",
    "recommended_mitigation": "<Compiler flags workarounds, e.g. -fno-strict-aliasing, or C++ source refactoring suggestions>"
}
Do not wrap your JSON in any extra conversational text. Output only the JSON object.
"""


class CompilerTriageAgent:
    """Orchestrates LLM triage with multi-model fallback chain and heuristic backup."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        primary_model: str = "gemini-2.5-flash",
        secondary_model: str = "gemini-1.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.primary_model = primary_model
        self.secondary_model = secondary_model

        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
            except Exception:
                pass

    def _call_gemini_model(self, model_name: str, prompt: str) -> Optional[str]:
        """Calls a specific Gemini model via the SDK."""
        if not self.api_key or genai is None:
            return None

        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            # Fallback to next model
            pass
        return None

    def _heuristic_triage(
        self,
        raw_crash_log: str,
        retrieved_context: List[Dict[str, Any]]
    ) -> TriageReport:
        """Deterministic heuristic triage fallback when LLM API keys are missing or offline."""
        top_match = retrieved_context[0] if retrieved_context else None
        
        lower_log = raw_crash_log.lower()
        if "template" in lower_log or "instantiate" in lower_log or "sfinae" in lower_log:
            category = "Frontend Parser / Template Metaprogramming"
        elif "insn" in lower_log or "recog" in lower_log or "cannot select" in lower_log:
            category = "Instruction Selection / Machine Lowering"
        elif "loop" in lower_log or "vector" in lower_log or "ivopts" in lower_log:
            category = "Loop Optimization & Vectorizer"
        elif "alias" in lower_log or "gvn" in lower_log or "tree-ssa" in lower_log:
            category = "Strict Aliasing / Tree-SSA Optimizer"
        elif "asm" in lower_log or "register" in lower_log:
            category = "Register Allocation / Inline Assembly"
        else:
            category = top_match.get("category", "General Compiler Backend Fault") if top_match else "Unclassified Compiler Crash"

        match_id = top_match.get("bug_id", "GCC-98512") if top_match else "UNKNOWN-ICE"
        score = top_match.get("score", 0.5) if top_match else 0.5
        conf_str = f"HIGH ({score:.2f})" if score > 0.7 else f"MEDIUM ({score:.2f})" if score > 0.3 else f"LOW ({score:.2f})"

        if top_match:
            root_cause = f"Correlated with historical bug {match_id}: {top_match.get('root_cause', '')}"
            mitigation = f"Suggested flags: {top_match.get('workaround', '-O2 or -fno-strict-aliasing')}"
        else:
            root_cause = "Compiler encountered an unhandled AST tree node or signal termination during optimization pass."
            mitigation = "Reduce optimization level to -O1 or -O0, or isolate crashing function using #pragma GCC optimize(\"O0\")."

        return TriageReport(
            bug_category=category,
            historical_match_id=match_id,
            similarity_confidence=conf_str,
            root_cause_analysis=root_cause,
            recommended_mitigation=mitigation,
        )

    def triage(
        self,
        raw_crash_log: str,
        retrieved_context: List[Dict[str, Any]],
    ) -> TriageReport:
        """Executes the triage fallback chain:

        1. Primary Gemini model
        2. Secondary Gemini fallback model
        3. Local heuristic compiler expert engine
        """
        # Format context prompt
        context_str = json.dumps(retrieved_context, indent=2)
        prompt = (
            f"=== COMPILER CRASH LOG ===\n{raw_crash_log}\n\n"
            f"=== RETRIEVED HISTORICAL CANDIDATES ===\n{context_str}\n\n"
            f"Analyze the crash and provide your structured JSON triage report."
        )

        # 1. Try Primary LLM
        for model in [self.primary_model, self.secondary_model]:
            raw_response = self._call_gemini_model(model, prompt)
            if raw_response:
                try:
                    # Clean markdown codeblocks if present
                    clean_json = re.sub(r"^```json\s*", "", raw_response)
                    clean_json = re.sub(r"\s*```$", "", clean_json).strip()
                    data = json.loads(clean_json)
                    return TriageReport(**data)
                except Exception:
                    continue

        # 2. Resilient Heuristic Fallback
        return self._heuristic_triage(raw_crash_log, retrieved_context)


if __name__ == "__main__":
    agent = CompilerTriageAgent()
    mock_log = (
        "internal compiler error: Segmentation fault in instantiate_class_template at cp/pt.c:11942\n"
        "0x8a9142 instantiate_class_template(tree_node*, tree_node*, tree_node*)\n"
        "Please submit a full bug report,"
    )
    mock_context = [
        {
            "bug_id": "GCC-98512",
            "score": 0.88,
            "category": "Frontend Parser / Template Substitution",
            "root_cause": "Infinite recursion in constexpr constraint satisfaction evaluation.",
            "workaround": "Set explicit recursion limits with -ftemplate-depth=256."
        }
    ]

    report = agent.triage(mock_log, mock_context)
    print(report.to_markdown())
