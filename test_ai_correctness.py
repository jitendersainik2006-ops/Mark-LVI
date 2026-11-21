"""
test_ai_correctness.py — AI Answer Quality, Reasoning & Tool Accuracy Verification Suite

Tests local Qwen2.5:3b against strict evaluation criteria:
1. Semantic correctness & relevance: Direct, truthful answers without fluff.
2. Deterministic calculations: Accurate math without hallucinating numbers.
3. Multi-turn conversation context retention: Tracking follow-up questions and implicit references.
4. Memory recall & personal facts: Calling memory tools for personal facts, not world knowledge.
5. Task execution & exact scope: Calling manage_tasks when requested without fabricating results.
6. Tool avoidance: Avoiding unnecessary tools on pure knowledge/science queries.
7. Handling of uncertain / unverified claims: Stating boundaries plainly instead of inventing facts.
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"
MODEL = "qwen2.5:3b"


def query_qwen(messages: list, tools: list = None, timeout: float = 120.0) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.2,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choice = data["choices"][0]
        return choice["message"]


def run_correctness_suite():
    print("=" * 70)
    print("  J.A.R.V.I.S. AI ANSWER QUALITY & CORRECTNESS EVALUATION SUITE")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Semantic Correctness & Deterministic Math Calculations
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: Semantic Correctness & Exact Math ---")
    sys_prompt = "You are J.A.R.V.I.S., an intelligent assistant. Give direct, concise, and accurate answers. Never guess or hallucinate."
    math_query = "Calculate 345 * 28 + 1400. Show your step-by-step calculation and final answer."
    msg = query_qwen([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": math_query},
    ])
    ans = msg.get("content", "").strip()
    print(f"User: '{math_query}'")
    print(f"Qwen: '{ans}'")
    assert "11060" in ans or "11,060" in ans, f"Expected 11060 in math answer, got: {ans}"
    print("✅ TEST 1 PASSED: Deterministic calculation evaluated accurately.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Multi-Turn Conversation Context Retention
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Multi-Turn Conversation Context Retention ---")
    history = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "My primary laptop is named 'Stark-Rig' and it runs Arch Linux."},
    ]
    resp1 = query_qwen(history)
    history.append({"role": "assistant", "content": resp1.get("content", "")})

    # Follow-up with implicit pronoun
    history.append({"role": "user", "content": "What is its operating system and what did I name it?"})
    resp2 = query_qwen(history)
    ans2 = resp2.get("content", "").strip()
    print(f"Follow-up: '{history[-1]['content']}'")
    print(f"Qwen: '{ans2}'")
    assert "Arch" in ans2 or "Linux" in ans2, f"Expected OS 'Arch Linux' retained, got: {ans2}"
    assert "Stark-Rig" in ans2 or "stark-rig" in ans2.lower(), f"Expected name 'Stark-Rig' retained, got: {ans2}"
    print("✅ TEST 2 PASSED: Multi-turn context and implicit references retained accurately.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Memory Tool Calling for Personal Information
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: Memory Tool Calling for Personal Inquiries ---")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "recall_memory",
                "description": "Look up personal facts or preferences stored about the user.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Keyword to look up"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the public web for news or articles.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
    ]
    mem_query = "What do you remember about my favorite food?"
    msg_mem = query_qwen(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": mem_query},
        ],
        tools=tools,
    )
    t_calls = msg_mem.get("tool_calls", [])
    print(f"User: '{mem_query}'")
    print(f"Tool calls returned: {[c['function']['name'] for c in t_calls]}")
    assert any(c["function"]["name"] in ("recall_memory", "manage_memory") for c in t_calls), (
        f"Expected recall_memory tool call, got: {t_calls}"
    )
    print("✅ TEST 3 PASSED: Memory tool correctly selected for personal inquiries.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Tool Avoidance on Pure Knowledge & Science Queries
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: Tool Avoidance on Pure Knowledge Queries ---")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from providers.engine_pipeline import PipelineEngine
    engine = PipelineEngine.__new__(PipelineEngine)
    engine._tools = tools

    know_query = "Explain photosynthesis briefly in one sentence."
    should_tools = engine._should_use_tools(know_query)
    print(f"User: '{know_query}'")
    print(f"PipelineEngine._should_use_tools: {should_tools}")
    assert not should_tools, f"Expected _should_use_tools to be False for pure science, got: {should_tools}"

    tools_for_query = tools if should_tools else None
    msg_know = query_qwen(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": know_query},
        ],
        tools=tools_for_query,
    )
    t_calls_know = msg_know.get("tool_calls", [])
    ans_know = msg_know.get("content", "").strip()
    print(f"Tool calls dispatched: {[c['function']['name'] for c in t_calls_know]}")
    print(f"Direct text: '{ans_know}'")
    assert not t_calls_know, f"Expected 0 tool calls for pure science query, got: {t_calls_know}"
    assert len(ans_know) > 15, "Expected meaningful text answer without tools"
    print("✅ TEST 4 PASSED: Unnecessary tool calls avoided on standard knowledge requests.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Task Manager Tool Calling
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 5: Task Manager Tool Invocation ---")
    task_tools = [
        {
            "type": "function",
            "function": {
                "name": "manage_tasks",
                "description": "Manage, create, list, status, approve, or cancel background tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["create", "list", "status", "approve", "cancel"]},
                        "title": {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
        }
    ]
    task_query = "List all my active background tasks."
    msg_task = query_qwen(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": task_query},
        ],
        tools=task_tools,
    )
    t_calls_task = msg_task.get("tool_calls", [])
    print(f"User: '{task_query}'")
    print(f"Tool calls: {[c['function']['name'] for c in t_calls_task]}")
    assert any(c["function"]["name"] == "manage_tasks" for c in t_calls_task), (
        f"Expected manage_tasks tool call, got: {t_calls_task}"
    )
    print("✅ TEST 5 PASSED: Task manager tool invoked accurately without fabricating status.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Honest Bounds on Unverified Information
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 6: Honest Bounds on Unknown / Unverified Information ---")
    unknown_query = "What is the secret passkey stored on the USB drive in my pocket right now?"
    msg_unkn = query_qwen([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": unknown_query},
    ])
    ans_unkn = msg_unkn.get("content", "").strip()
    print(f"User: '{unknown_query}'")
    print(f"Qwen: '{ans_unkn}'")
    unkn_lower = ans_unkn.lower()
    refusal_words = [
        "cannot", "don't know", "do not know", "unable", "not able",
        "no access", "cannot verify", "don't have access", "do not have access",
        "have no access", "only you have access"
    ]
    assert any(w in unkn_lower for w in refusal_words), f"Expected honest boundary acknowledgement, got: {ans_unkn}"
    print("✅ TEST 6 PASSED: Model honestly acknowledges boundaries on unverified private data.")

    print("\n" + "=" * 70)
    print("  🎉 ALL 6 AI CORRECTNESS & REASONING EVALUATION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_correctness_suite()
