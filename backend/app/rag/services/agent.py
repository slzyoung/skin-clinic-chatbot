"""ReAct AI Agent for complex multi-step medical queries.

Inspired by Open-Brain's agent.py, adapted for ERHA medical domain.
Enabled via RAG_AGENT_ENABLED=true environment variable.

The agent can orchestrate multiple tool calls to answer complex queries
like: "Apa krim ERHA untuk acne dan apa kontraindikasinya untuk ibu hamil?"

Agent flow: Question → Reason → Tool Call → Observe → Reason → ... → Answer
"""

import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.rag.config import settings
from app.rag.services.interfaces import BaseLLMAdapter
from app.rag.services.rag_retriever import HybridRetriever
from app.rag.services.intent import QueryIntentDetector, QueryIntent, get_current_time_period, get_time_greeting_response


# ── Agent System Prompt ──────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """<role>
You are ERHA Medical Assistant Agent, an expert clinical decision support and product knowledge assistant exclusively for ERHA Doctors and Clinicians (PT Arya Noble).
The user is ALWAYS an ERHA Doctor/Clinician consulting on ERHA skincare products, clinical protocols, treatments, active ingredients, dosages, and contraindications for their patients. This assistant is NOT used by patients directly.
You have access to tools to search the ERHA product, treatment, and safety knowledge base.
</role>

<language_rules>
- Chatbot ini digunakan KHUSUS OLEH DOKTER ERHA (bukan pasien umum). Gunakan gaya komunikasi profesional medis klinis antar sejawat (medical assistant to doctor).
- Selalu sapa pengguna dengan sebutan 'Dokter' atau 'Dok' jika memerlukan sapaan.
- Bahasa utama yang digunakan adalah Bahasa Indonesia medis yang jelas dan natural.
- HANYA sertakan sapaan pembuka (seperti 'Halo Dok! Selamat siang') jika Dokter secara eksplisit menyapa di awal turn ini ATAU pada pesan pertama percakapan. Jika percakapan sudah berlangsung (history > 0) atau Dokter langsung bertanya tanpa kata sapaan, DILARANG mengulang sapaan pembuka.
- HANYA gunakan Bahasa Inggris jika Dokter mengajukan pertanyaan dalam Bahasa Inggris.
</language_rules>

<parallelism_guideline>
DEFAULT TO PARALLEL: Unless you have a specific reason why operations MUST be sequential, always execute multiple tools simultaneously... parallel tool execution can be 3-5x faster.
If the query requires searching multiple topics (e.g., comparing products, checking both treatments and contraindications, or looking up multiple ingredients), execute ALL necessary tool calls in a SINGLE turn. Do NOT make separate sequential turns when parallel execution is possible.
</parallelism_guideline>

<strict_rules>
1. Answer ONLY what the user asked. Be concise, direct, and clinically accurate.
2. Do not provide unsolicited product recommendations, treatment regimens, or non-medical filler.
3. HANYA sertakan sapaan jika Dokter menyapa di turn ini atau jika ini percakapan pertama. Jika percakapan sudah berlangsung, DILARANG mengulang sapaan pembuka.
4. Never substitute one product or treatment name for another. Preserve exact clinical names from context.
5. If requested information is not available in the knowledge base, state so clearly. Do not speculate.
6. For simple factual questions, keep the final answer to 1-3 sentences maximum.
7. Saat merekomendasikan produk/tindakan yang memiliki image_url di observasi database, selalu tampilkan gambar dalam format Markdown: `![Nama Produk](image_url)` tepat di bawah teks rekomendasi produk agar dokter dapat melihat bentuk fisik dan kemasan produk. Jika di database tidak terdapat image_url, cukup jawab dengan teks saja (jangan mengarang URL gambar).
8. DILARANG menambahkan saran atau disclaimer pasien seperti 'konsultasikan dengan dokter', 'lakukan konsultasi lebih lanjut', dsb. karena user adalah DOKTER itu sendiri.
9. DILARANG menempelkan kalimat penutup basa-basi seperti 'Jika ada pertanyaan lebih lanjut, silakan beri tahu.' Akhiri jawaban langsung pada poin fakta medis.
</strict_rules>

<conversation_history>
{history}
</conversation_history>"""

MEDICAL_AGENT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search ERHA product knowledge base for skincare product information, ingredients, usage, and recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for skincare products"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "One sentence explanation as to why this search tool is being used"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_treatments",
            "description": "Search ERHA clinical treatment/procedure database for in-clinic aesthetic procedures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for clinical treatments"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "One sentence explanation as to why this search tool is being used"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_contraindications",
            "description": "Search for safety information, contraindications, side effects, and pregnancy/lactation warnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for contraindications and safety"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "One sentence explanation as to why this search tool is being used"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


class MedicalAgent:
    """ReAct agent with medical knowledge base tools for multi-step reasoning and parallel execution."""

    def __init__(
        self,
        retriever: HybridRetriever,
        llm_adapter: BaseLLMAdapter,
        max_iterations: int = 5,
    ):
        self.retriever = retriever
        self.llm_adapter = llm_adapter
        self.max_iterations = max_iterations
        self.tools_schema = MEDICAL_AGENT_TOOLS_SCHEMA

    def _search_knowledge_base(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Tool: Semantic + BM25 hybrid search over the ERHA knowledge base."""
        try:
            result = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                filter_metadata=filter_metadata,
                rerank=True,
                rerank_top_n=top_k,
            )
            hits = result.get("results", [])
            if not hits:
                return "No relevant information found in the knowledge base."

            formatted = []
            for i, hit in enumerate(hits[:5], 1):
                meta = hit.get("metadata", {})
                source = meta.get("source_file", "unknown")
                section = meta.get("section", "General")
                text = hit.get("text", "")[:500]
                formatted.append(
                    f"[{i}] Source: {source} | Section: {section}\n{text}"
                )
            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Agent tool search_knowledge_base failed: {e}")
            return f"Search failed: {str(e)}"

    def _search_products(self, query: str) -> str:
        """Tool: Search ERHA product knowledge base for skincare recommendations."""
        return self._search_knowledge_base(
            query=query,
            top_k=5,
            filter_metadata={"type": "product"},
        )

    def _search_treatments(self, query: str) -> str:
        """Tool: Search ERHA treatment/procedure database."""
        return self._search_knowledge_base(
            query=query,
            top_k=5,
            filter_metadata={"type": "treatment"},
        )

    def _search_contraindications(self, query: str) -> str:
        """Tool: Search for safety information, contraindications, and side effects."""
        safety_query = f"kontraindikasi efek samping keamanan {query}"
        return self._search_knowledge_base(query=safety_query, top_k=5)

    def _build_tool_descriptions(self) -> str:
        """Build tool descriptions for the ReAct prompt with parallel execution support."""
        return """Available tools:
1. search_products(query) - Search ERHA product knowledge base for skincare product information, ingredients, usage, and recommendations.
2. search_treatments(query) - Search ERHA clinical treatment/procedure database for in-clinic aesthetic procedures.
3. search_contraindications(query) - Search for safety information, contraindications, side effects, and pregnancy/lactation warnings.

PARALLEL TOOL CALLING INSTRUCTION:
DEFAULT TO PARALLEL: Unless you have a specific reason why operations MUST be sequential, always execute multiple tools simultaneously... parallel tool execution can be 3-5x faster.
When a question requires gathering multiple pieces of evidence (e.g., comparing multiple items, checking product ingredients + contraindications together), call ALL relevant tools in a SINGLE turn.

Format for single or multiple parallel tool calls:
Thought: [your reasoning about what information is needed and why tools are executed in parallel]
Action: [tool_name_1]
Action Input: [query_1]
Action: [tool_name_2]
Action Input: [query_2]

Or JSON tool call list format:
```json
[
  {"name": "tool_1", "arguments": {"query": "query_1"}},
  {"name": "tool_2", "arguments": {"query": "query_2"}}
]
```

When you have collected all observations and have enough information:
Thought: I now have enough information to answer.
Final Answer: [your comprehensive, grounded response in markdown format]"""

    def _parse_agent_actions(self, response: str) -> List[Dict[str, str]]:
        """Parse all actions from the agent's response (supports multiple ReAct actions and JSON tool call arrays)."""
        actions = []

        # 1. Try parsing JSON array or JSON object
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                blocks = cleaned.split("```json")
                for block in blocks[1:]:
                    json_str = block.split("```")[0].strip()
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, list):
                            for item in data:
                                act = item.get("name") or item.get("action")
                                args = item.get("arguments") or item.get("parameters") or item.get("input")
                                inp = args.get("query") if isinstance(args, dict) else str(args or "")
                                if act and inp:
                                    actions.append({"action": str(act).strip(), "input": str(inp).strip()})
                        elif isinstance(data, dict):
                            act = data.get("name") or data.get("action")
                            args = data.get("arguments") or data.get("parameters") or data.get("input")
                            inp = args.get("query") if isinstance(args, dict) else str(args or "")
                            if act and inp:
                                actions.append({"action": str(act).strip(), "input": str(inp).strip()})
                    except Exception:
                        pass
            elif cleaned.startswith("[") and cleaned.endswith("]"):
                data = json.loads(cleaned)
                if isinstance(data, list):
                    for item in data:
                        act = item.get("name") or item.get("action")
                        args = item.get("arguments") or item.get("parameters") or item.get("input")
                        inp = args.get("query") if isinstance(args, dict) else str(args or "")
                        if act and inp:
                            actions.append({"action": str(act).strip(), "input": str(inp).strip()})
            elif cleaned.startswith("{") and cleaned.endswith("}"):
                data = json.loads(cleaned)
                act = data.get("name") or data.get("action")
                args = data.get("arguments") or data.get("parameters") or data.get("input")
                inp = args.get("query") if isinstance(args, dict) else str(args or "")
                if act and inp:
                    actions.append({"action": str(act).strip(), "input": str(inp).strip()})
        except Exception:
            pass

        if actions:
            return actions

        # 2. Text ReAct format parsing fallback (supports multiple Action: / Action Input: pairs)
        lines = response.strip().split("\n")
        current_action = None

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("Action:"):
                current_action = line_stripped[len("Action:"):].strip()
            elif line_stripped.startswith("Action Input:") and current_action:
                action_input = line_stripped[len("Action Input:"):].strip()
                actions.append({"action": current_action, "input": action_input})
                current_action = None

        return actions

    def _execute_tool(self, action: str, action_input: str) -> str:
        """Execute a tool by name."""
        tool_map = {
            "search_products": self._search_products,
            "search_treatments": self._search_treatments,
            "search_contraindications": self._search_contraindications,
        }

        tool_func = tool_map.get(action)
        if tool_func is None:
            logger.warning(f"Unknown tool '{action}', falling back to general search.")
            return self._search_knowledge_base(action_input)

        return tool_func(action_input)

    def _execute_tools_parallel(self, actions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Execute multiple tool calls concurrently using ThreadPoolExecutor."""
        import concurrent.futures

        if not actions:
            return []

        if len(actions) == 1:
            act = actions[0]
            obs = self._execute_tool(act["action"], act["input"])
            return [{
                "tool": act["action"],
                "input": act["input"],
                "observation": obs
            }]

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(actions), 5)) as executor:
            future_to_action = {
                executor.submit(self._execute_tool, act["action"], act["input"]): act
                for act in actions
            }
            for future in concurrent.futures.as_completed(future_to_action):
                act = future_to_action[future]
                try:
                    obs = future.result()
                except Exception as exc:
                    logger.error(f"Parallel tool {act['action']} execution error: {exc}")
                    obs = f"Search failed: {str(exc)}"
                results.append({
                    "tool": act["action"],
                    "input": act["input"],
                    "observation": obs
                })
        return results

    def run(
        self,
        question: str,
        history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Run the ReAct agent loop with parallel tool calling support.
        Returns dict with 'answer', 'sources', and 'agent' flag.
        Falls back to None if agent fails (caller should use standard pipeline).
        """
        if history is None:
            history = []

        # Fast-path for pure greeting queries
        intent, _ = QueryIntentDetector.detect(question)
        if intent == QueryIntent.GREETING:
            greeting_ans = get_time_greeting_response(question)
            logger.info(f"Agent detected pure greeting ('{question}'). Returning warm time-adjusted response: '{greeting_ans}'")
            return {
                "answer": greeting_ans,
                "sources": [],
                "agent": True,
                "iterations": 1,
            }

        history_str = ""
        if history:
            for msg in history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"
        else:
            history_str = "(no previous conversation)\n"

        system = AGENT_SYSTEM_PROMPT.format(history=history_str)
        tool_descriptions = self._build_tool_descriptions()

        # Build initial prompt
        conversation = f"{system}\n\n{tool_descriptions}\n\nUser question: {question}\n\n"
        all_observations = []

        logger.info(
            f"\n"
            f"================================================================================\n"
            f"🤖 [REACT MEDICAL AGENT] Multi-Step Tool Reasoning Started\n"
            f"--------------------------------------------------------------------------------\n"
            f"❓ Doctor Query     : \"{question}\"\n"
            f"💬 History Length   : {len(history)} message(s)\n"
            f"================================================================================"
        )

        try:
            for iteration in range(self.max_iterations):
                logger.info(f"🔄 [AGENT REASONING] Iteration {iteration + 1}/{self.max_iterations}...")

                # Generate agent response
                response = self.llm_adapter.generate(conversation)
                conversation += response + "\n"

                # Check for final answer
                if "Final Answer:" in response:
                    final_answer_start = response.index("Final Answer:") + len("Final Answer:")
                    answer = response[final_answer_start:].strip()
                    logger.info(
                        f"\n"
                        f"================================================================================\n"
                        f"🏁 [AGENT FINAL ANSWER GENERATED] (Completed in {iteration + 1} iterations)\n"
                        f"--------------------------------------------------------------------------------\n"
                        f"📝 Answer Output :\n{answer}\n"
                        f"================================================================================\n"
                    )
                    return {
                        "answer": answer,
                        "sources": all_observations,
                        "agent": True,
                        "iterations": iteration + 1,
                    }

                # Parse and execute action(s) in parallel
                parsed_actions = self._parse_agent_actions(response)
                if parsed_actions:
                    tools_display = ", ".join([f"{a['action']}('{a['input']}')" for a in parsed_actions])
                    logger.info(f"⚡ [PARALLEL TOOL EXECUTION] Calling {len(parsed_actions)} tool(s) simultaneously: {tools_display}")
                    parallel_results = self._execute_tools_parallel(parsed_actions)

                    obs_lines = []
                    for res in parallel_results:
                        all_observations.append({
                            "tool": res["tool"],
                            "input": res["input"],
                            "output_preview": res["observation"][:200],
                        })
                        obs_lines.append(f"Observation ({res['tool']} for '{res['input']}'):\n{res['observation']}")
                        logger.info(f"   📦 [{res['tool']}] -> Returned observation ({len(res['observation'])} chars)")

                    conversation += "\n\n".join(obs_lines) + "\n\n"
                else:
                    # No action parsed and no final answer — force completion
                    logger.warning("Agent produced no action or final answer. Forcing completion.")
                    conversation += (
                        "You did not use a tool or provide a Final Answer. "
                        "Please provide your Final Answer now based on what you know.\n\n"
                    )

            # Max iterations reached — extract whatever we have
            logger.warning(f"Agent reached max iterations ({self.max_iterations}).")
            final_prompt = conversation + (
                "\nYou have reached the maximum number of reasoning steps. "
                "Please provide your Final Answer now based on the observations collected.\n\n"
                "Final Answer:"
            )
            final_response = self.llm_adapter.generate(final_prompt)
            final_answer_cleaned = final_response.strip()
            logger.info(
                f"\n"
                f"================================================================================\n"
                f"🏁 [AGENT FORCED FINAL ANSWER] (Max iterations {self.max_iterations} reached)\n"
                f"--------------------------------------------------------------------------------\n"
                f"📝 Answer Output :\n{final_answer_cleaned}\n"
                f"================================================================================\n"
            )
            return {
                "answer": final_answer_cleaned,
                "sources": all_observations,
                "agent": True,
                "iterations": self.max_iterations,
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return None
