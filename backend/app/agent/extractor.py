import json
import logging
from typing import List, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.memory import ChatMessage, MemoryCreate, MemoryType

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """You are a memory extraction specialist. Analyze the conversation and extract facts worth remembering for future sessions.

Extract memories in these categories:
- preference: coding style, language preferences, tool choices
- decision: architectural decisions, technology choices made
- bug_fix: bugs identified and how they were fixed
- pattern: reusable code patterns or approaches discussed
- general: other relevant facts

Return ONLY a JSON array (no markdown, no explanation):
[{"content": "...", "memory_type": "...", "importance_score": 0.0-1.0}]

Rules:
- Only extract concrete, reusable facts (not small talk or pleasantries)
- importance_score: 0.9 for critical decisions, 0.7 for patterns, 0.5 for general facts
- Maximum 5 memories per conversation
- If nothing worth remembering: return []"""


class MemoryExtractor:
    def __init__(self, client: AsyncOpenAI):
        self._client = client

    async def extract_memories(
        self,
        conversation: List[ChatMessage],
        user_id: str,
        project_id: Optional[str] = None,
    ) -> List[MemoryCreate]:
        """Extract memorable facts from a conversation turn without prompting the user."""
        if not conversation:
            return []

        conv_text = "\n".join(f"{msg.role.upper()}: {msg.content}" for msg in conversation)

        try:
            response = await self._client.chat.completions.create(
                model=settings.QWEN_REASONING_MODEL,
                messages=[
                    {"role": "system", "content": _EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Conversation to analyze:\n\n{conv_text}"},
                ],
                max_tokens=1024,
                temperature=0.1,  # deterministic extraction
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if model wraps JSON anyway
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            extracted = json.loads(raw)
            if not isinstance(extracted, list):
                return []

            memories = []
            for item in extracted[:5]:  # enforce max 5
                try:
                    mem_type = MemoryType(item.get("memory_type", "general"))
                    memories.append(
                        MemoryCreate(
                            user_id=user_id,
                            project_id=project_id,
                            content=str(item["content"]),
                            memory_type=mem_type,
                            importance_score=float(item.get("importance_score", 0.5)),
                        )
                    )
                except (KeyError, ValueError) as e:
                    logger.debug("Skipping malformed extraction item: %s — %s", item, e)

            return memories

        except json.JSONDecodeError as e:
            logger.warning("Memory extraction returned non-JSON: %s", e)
            return []
        except Exception as e:
            logger.error("Memory extraction failed: %s", e)
            return []
