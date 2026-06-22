"""
Qwen Cloud Custom Skills for DevMemory Agent.
These are registered as callable tools in the qwen3.7-max agent loop,
going beyond standard function calling into Qwen's native skill system.
"""

DEV_MEMORY_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "recall_project_context",
            "description": "Recall all stored memories for a specific project, ranked by relevance to the current task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project identifier",
                    },
                    "current_task": {
                        "type": "string",
                        "description": "What the developer is working on right now",
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["preference", "decision", "bug_fix", "pattern", "general"],
                        },
                        "description": "Filter by memory type (optional)",
                    },
                },
                "required": ["project_id", "current_task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_developer_insight",
            "description": "Explicitly save an important insight, decision, or pattern for future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "insight": {
                        "type": "string",
                        "description": "The insight to remember",
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["preference", "decision", "bug_fix", "pattern"],
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 1.0,
                    },
                },
                "required": ["insight", "memory_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_similar_problems",
            "description": "Search memory for similar problems the developer has solved before.",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem_description": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["problem_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_memory_health",
            "description": "Check memory statistics and identify memories at risk of being forgotten.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "show_at_risk": {"type": "boolean", "default": True},
                },
                "required": ["user_id"],
            },
        },
    },
]
