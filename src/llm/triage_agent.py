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

import requests
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
    provider: str = Field(
        default="Gemini",
        description="LLM provider that performed the triage (e.g. Gemini, Grok, or Offline Heuristic)"
    )

    def to_markdown(self) -> str:
        """Renders the triage report in clean GitHub Markdown format."""
        return (
            f"### [TRIAGE REPORT] Compiler Crash Analysis\n\n"
            f"- **Triage Provider:** `{self.provider}`\n"
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
    """Orchestrates multi-provider LLM triage (Gemini + Grok) with heuristic backup."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        grok_api_key: Optional[str] = None,
        primary_model: str = "gemini-2.5-flash",
        secondary_model: str = "gemini-1.5-flash",
        grok_model: str = "grok-2-latest",
    ):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.grok_api_key = grok_api_key or os.getenv("GROK_API_KEY", "") or os.getenv("XAI_API_KEY", "")
        self.primary_model = primary_model
        self.secondary_model = secondary_model
        self.grok_model = grok_model

        if self.gemini_api_key and genai is not None:
            try:
                genai.configure(api_key=self.gemini_api_key)
            except Exception:
                pass

    def _call_gemini_model(self, model_name: str, prompt: str) -> Optional[str]:
        """Calls a specific Gemini model via the SDK."""
        if not self.gemini_api_key or genai is None:
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

    def _call_grok_model(self, prompt: str) -> Optional[str]:
        """Calls xAI's Grok API via standard OpenAI-compatible completions endpoint."""
        if not self.grok_api_key:
            return None

        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.grok_api_key}",
        }
        payload = {
            "model": self.grok_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except Exception:
            # Fallback to next tier
            pass
        return None

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Extracts and parses JSON from raw LLM responses."""
        try:
            clean = re.sub(r"^```json\s*", "", raw_text.strip())
            clean = re.sub(r"\s*```$", "", clean).strip()
            # If wrapped in other markdown backticks
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(clean)
        except Exception:
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
            provider="Offline Heuristic Engine",
        )

    def triage(
        self,
        raw_crash_log: str,
        retrieved_context: List[Dict[str, Any]],
    ) -> TriageReport:
        """Executes the multi-provider triage fallback chain:

        1. Primary Chain: Gemini (Gemini 2.5 Flash -> Gemini 1.5 Flash)
        2. Secondary Chain: Grok / xAI (Grok 2)
        3. Tertiary Chain: Deterministic Local Heuristic Engine
        """
        # Format context prompt
        context_str = json.dumps(retrieved_context, indent=2)
        prompt = (
            f"=== COMPILER CRASH LOG ===\n{raw_crash_log}\n\n"
            f"=== RETRIEVED HISTORICAL CANDIDATES ===\n{context_str}\n\n"
            f"Analyze the crash and provide your structured JSON triage report."
        )

        # 1. Primary Chain: Gemini Models
        for model in [self.primary_model, self.secondary_model]:
            raw_response = self._call_gemini_model(model, prompt)
            if raw_response:
                parsed = self._clean_and_parse_json(raw_response)
                if parsed:
                    parsed["provider"] = f"Gemini ({model})"
                    return TriageReport(**parsed)

        # 2. Secondary Chain: Grok (xAI)
        raw_grok = self._call_grok_model(prompt)
        if raw_grok:
            parsed = self._clean_and_parse_json(raw_grok)
            if parsed:
                parsed["provider"] = f"xAI Grok ({self.grok_model})"
                return TriageReport(**parsed)

        # 3. Tertiary Chain: Resilient Heuristic Fallback
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
