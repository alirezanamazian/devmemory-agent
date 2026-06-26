import asyncio
import json
import logging
from typing import List, Optional
from uuid import uuid4

from openai import AsyncOpenAI

from app.agent.extractor import MemoryExtractor
from app.config import settings
from app.core.context_manager import ContextWindowManager
from app.core.memory_engine import MemoryEngine
from app.models.memory import ChatMessage, ChatRequest, ChatResponse
from app.skills.dev_skills import DEV_MEMORY_SKILLS

logger = logging.getLogger(__name__)


class DevMemoryAgent:
    def __init__(
        self,
        memory_engine: MemoryEngine,
        context_manager: ContextWindowManager,
        extractor: MemoryExtractor,
        qwen_client: AsyncOpenAI,
    ):
        self._memory = memory_engine
        self._ctx = context_manager
        self._extractor = extractor
        self._client = qwen_client
        # Exposed so tests can await the background extraction task instead
        # of racing it; not used by production code paths.
        self.last_extraction_task: Optional["asyncio.Task[None]"] = None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Full agent loop with memory-augmented generation:
        1. Retrieve relevant memories (vector + rerank)
        2. Fit top memories in the context budget
        3. Inject memories into the system prompt
        4. Call qwen3.7-max with custom skills enabled (tool_choice=auto)
        5. Handle any tool calls the model makes
        6. Extract new memories from this turn (autonomous, non-blocking on failure)
        7. Save new memories + reinforce the ones we used
        """
        search_results = await self._memory.search_memories(
            query=request.message,
            user_id=request.user_id,
            project_id=request.project_id,
            top_k=20,
        )

        selected_memories = await self._ctx.select_memories(
            search_results, max_tokens=settings.MEMORY_CONTEXT_MAX_TOKENS
        )

        memory_context = self._ctx.format_memories_for_prompt(selected_memories)
        system_prompt = self._build_system_prompt(memory_context)

        response_text = await self._call_qwen_with_tools(system_prompt, request)

        # Only the user's own message is a source of new facts. The assistant's
        # reply often restates memories already in storage (e.g. "here's a
        # summary of everything you've told me") — feeding that back into the
        # extractor re-saves the same facts as if they were new.
        conversation = [ChatMessage(role="user", content=request.message)]
        # Extraction makes another Qwen call and embeds+saves each memory it
        # finds — none of that affects this response, so it runs after we
        # return instead of making the user wait on it.
        task = asyncio.create_task(
            self._extract_and_save(conversation, request.user_id, request.project_id)
        )
        task.add_done_callback(self._log_background_task_error)
        self.last_extraction_task = task

        # Reinforce the top-5 memories we actually surfaced in this response
        for result in search_results[:5]:
            try:
                await self._memory.reinforce_memory(result.memory.id)
            except Exception as e:
                logger.debug("Reinforce failed for %s: %s", result.memory.id, e)

        return ChatResponse(
            session_id=request.session_id or str(uuid4()),
            response=response_text,
            memories_used=selected_memories,
            # Extraction is now async — always 0 here, the saved memories show
            # up in the memory panel once the background task finishes.
            memories_extracted=0,
        )

    async def _extract_and_save(
        self, conversation: List[ChatMessage], user_id: str, project_id: Optional[str]
    ) -> None:
        new_memories = await self._extractor.extract_memories(conversation, user_id, project_id)
        for mem in new_memories:
            try:
                await self._memory.save_memory(mem)
            except Exception as e:
                logger.warning("Failed to save extracted memory: %s", e)

    @staticmethod
    def _log_background_task_error(task: "asyncio.Task[None]") -> None:
        if not task.cancelled() and task.exception():
            logger.error("Background memory extraction failed: %s", task.exception())

    async def _call_qwen_with_tools(self, system_prompt: str, request: ChatRequest) -> str:
        # qwen3.7-max occasionally returns an empty completion with no tool
        # call and no error — retry once before falling back to a generic
        # acknowledgment so the user never sees a blank response bubble.
        text = await self._complete_with_tools_once(system_prompt, request)
        if not text.strip():
            logger.warning("Qwen returned an empty completion, retrying once")
            text = await self._complete_with_tools_once(system_prompt, request)
        return text.strip() or "Got it — noted."

    async def _complete_with_tools_once(self, system_prompt: str, request: ChatRequest) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message},
        ]

        response = await self._client.chat.completions.create(
            model=settings.QWEN_REASONING_MODEL,
            messages=messages,
            tools=DEV_MEMORY_SKILLS,
            tool_choice="auto",
            max_tokens=2048,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message.model_dump())
            for tool_call in choice.message.tool_calls:
                tool_result = await self._dispatch_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                    request,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                })

            follow_up = await self._client.chat.completions.create(
                model=settings.QWEN_REASONING_MODEL,
                messages=messages,
                max_tokens=2048,
            )
            return follow_up.choices[0].message.content or ""

        return choice.message.content or ""

    async def _dispatch_tool(self, name: str, args: dict, request: ChatRequest) -> dict:
        """Route tool calls from qwen3.7-max to memory engine operations."""
        try:
            if name == "recall_project_context":
                memories = await self._memory.search_memories(
                    query=args["current_task"],
                    user_id=request.user_id,
                    project_id=args.get("project_id", request.project_id),
                )
                return {"memories": [r.memory.content for r in memories[:5]]}

            elif name == "save_developer_insight":
                from app.models.memory import MemoryCreate, MemoryType

                mem = MemoryCreate(
                    user_id=request.user_id,
                    project_id=request.project_id,
                    content=args["insight"],
                    memory_type=MemoryType(args["memory_type"]),
                    importance_score=args.get("importance", 0.7),
                )
                saved = await self._memory.save_memory(mem)
                return {"saved": True, "memory_id": saved.id}

            elif name == "find_similar_problems":
                results = await self._memory.search_memories(
                    query=args["problem_description"],
                    user_id=request.user_id,
                    top_k=args.get("top_k", 3),
                )
                return {"similar_problems": [r.memory.content for r in results]}

            elif name == "get_memory_health":
                return await self._memory.get_stats(request.user_id)

            return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            logger.error("Tool dispatch failed for %s: %s", name, e)
            return {"error": str(e)}

    def _build_system_prompt(self, memory_context: str) -> str:
        base = (
            "You are DevMemory, an AI coding assistant with persistent memory.\n"
            "You remember everything from past sessions and use that context to give better answers.\n\n"
        )
        if memory_context:
            base += (
                "## Your Memory Context (from past sessions)\n"
                f"{memory_context}\n\n"
                "Use these memories to personalize your response. Reference them when relevant.\n"
            )
        base += (
            "\nBe concise, technical, and leverage your memory to avoid repeating "
            "questions you already know the answer to."
        )
        return base
