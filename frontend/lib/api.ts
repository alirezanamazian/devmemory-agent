export interface MemoryResponse {
  id: string;
  user_id: string;
  project_id?: string | null;
  content: string;
  summary?: string | null;
  memory_type: string;
  importance_score: number;
  decay_rate: number;
  access_count: number;
  created_at: string;
  last_accessed: string;
}

export interface MemoryStats {
  total_memories: number;
  avg_importance: number | null;
  oldest_memory: string | null;
  newest_memory: string | null;
  memories_at_risk: number;
  memories_by_type: Record<string, number> | null;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  memories_used: MemoryResponse[];
  memories_extracted: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function sendChatMessage(userId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchMemories(userId: string): Promise<MemoryResponse[]> {
  const res = await fetch(`${API_URL}/api/v1/memories/${encodeURIComponent(userId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch memories: ${res.status}`);
  }
  return res.json();
}

export async function fetchMemoryStats(userId: string): Promise<MemoryStats> {
  const res = await fetch(`${API_URL}/api/v1/memories/${encodeURIComponent(userId)}/stats`);
  if (!res.ok) {
    throw new Error(`Failed to fetch stats: ${res.status}`);
  }
  return res.json();
}
