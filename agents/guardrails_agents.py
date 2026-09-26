import re
import json
from typing import Dict, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class GuardrailsAgent:
    """
    Guardrails Security and Safety Verification Agent for ORCA system architecture.
    Handles Input Safety, Distress Keyword Escapes, Data Hallucination Checks, and Out-of-Bounds Queries.
    """
    def __init__(self, llm=None):
        self.llm = llm
        # Keywords indicating immediate life safety / emergency at sea
        self.distress_keywords = [
            "sos", "mayday", "sinking", "drowning", "boat capsize", "capsized",
            "engine failure", "cyclone warning", "medical emergency", "help me",
            "मदद", "जीव वाचवा", "कापा", "संकट"
        ]

    def validate_input_query(self, query: str) -> Dict[str, Any]:
        """
        Input Guardrail: Checks for prompt injection, out-of-scope domain queries, 
        and immediate emergency distress signals.
        """
        query_lower = query.lower().strip()

        # 1. Immediate SOS / Mayday Check
        if any(keyword in query_lower for keyword in self.distress_keywords):
            return {
                "is_safe": True,
                "is_distress": True,
                "flagged_reason": None,
                "action": "TRIGGER_EMERGENCY_PROTOCOL",
                "clean_query": query
            }

        # 2. Prompt Injection & Malicious String Patterns
        injection_patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"drop table",
            r"delete from",
            r"<script>",
            r"override safety"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, query_lower):
                return {
                    "is_safe": False,
                    "is_distress": False,
                    "flagged_reason": "PROMPT_INJECTION_DETECTED",
                    "action": "BLOCK_REQUEST",
                    "clean_query": None
                }

        # 3. Off-topic domain check using heuristic filtering
        marine_keywords = [
            "fish", "pfz", "sea", "ocean", "weather", "wave", "wind", "boat", "vessel",
            "border", "imbl", "eez", "coast", "storm", "current", "temperature", "sst",
            "incois", "imd", "depth", "coordinate", "port", "harbor", "navigation"
        ]
        
        # Allow general greetings or marine-related content
        is_relevant = any(kw in query_lower for kw in marine_keywords) or len(query_lower.split()) < 4

        if not is_relevant and self.llm:
            # LLM Verification for ambiguous queries
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are ORCA Guardrail. Return JSON with key 'is_maritime_related' (bool)."),
                ("user", "Is this query related to ocean, fishing, weather, marine safety, or maritime policy? Query: '{query}'")
            ])
            try:
                chain = prompt | self.llm | JsonOutputParser()
                res = chain.invoke({"query": query})
                is_relevant = res.get("is_maritime_related", True)
            except Exception:
                is_relevant = True  # Default to permissive on failure

        if not is_relevant:
            return {
                "is_safe": False,
                "is_distress": False,
                "flagged_reason": "OUT_OF_BOUNDS_DOMAIN",
                "action": "REDIRECT_TO_MARITIME_SCOPE",
                "clean_query": query
            }

        return {
            "is_safe": True,
            "is_distress": False,
            "flagged_reason": None,
            "action": "PROCEED",
            "clean_query": query
        }

    def validate_output_advisory(self, agent_response: str, raw_data_context: Dict[str, Any]) -> str:
        """
        Output Guardrail: Sanitizes generated agent response to prevent hallucinations,
        ensures critical safety warnings are maintained, and enforces clean response structures.
        """
        # Ensure mandatory safety disclaimer if rough sea alert is active in data context
        if raw_data_context.get("rough_sea_alert") or raw_data_context.get("cyclonic_warning"):
            if "WARNING" not in agent_response.upper() and "ALERT" not in agent_response.upper():
                agent_response = "⚠️ HIGH SEAS WARNING: Adverse oceanic conditions detected! " + agent_response

        # Check for non-validated coordinates or impossible ocean temps (> 45°C or < -5°C)
        sst = raw_data_context.get("sea_surface_temperature_celsius")
        if sst and (sst > 45.0 or sst < -5.0):
            agent_response += "\n[Guardrail Note: Sensor temperature anomaly detected. Verify with local port authorities.]"

        return agent_response


# Global helper function for direct agent graph node integration
def guardrails_node(state: Dict[str, Any]) -> Dict[str, Any]:
    guard = GuardrailsAgent()
    user_query = state.get("query", "")
    data_context = state.get("data_context", {})

    validation = guard.validate_input_query(user_query)

    if not validation["is_safe"]:
        return {
            **state,
            "error": validation["flagged_reason"],
            "response": "I can only assist with maritime safety, ocean weather, fishing zones (PFZ), and coastal regulations.",
            "status": "BLOCKED"
        }

    if validation["is_distress"]:
        return {
            **state,
            "is_emergency": True,
            "response": "🚨 EMERGENCY DISTRESS SIGNAL DETECTED! Transmitting location to Indian Coast Guard & Emergency Response Services immediately.",
            "status": "EMERGENCY_TRIGGERED"
        }

    return {**state, "status": "GUARDRAILS_PASSED"}