"use client";

import { useEffect, useState } from "react";
import { fetchMemories, fetchMemoryStats, MemoryResponse, MemoryStats } from "@/lib/api";
import { MemoryStatsRow } from "@/components/MemoryStatsRow";
import { MemoryDecayChart } from "@/components/MemoryDecayChart";
import { MemoryCard } from "@/components/MemoryCard";

export function MemoryPanel({ userId, refreshKey }: { userId: string; refreshKey: number }) {
  const [memories, setMemories] = useState<MemoryResponse[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      return;
    }
    let cancelled = false;

    async function load() {
      try {
        const [memList, statsResult] = await Promise.all([
          fetchMemories(userId),
          fetchMemoryStats(userId),
        ]);
        if (!cancelled) {
          setMemories(memList);
          setStats(statsResult);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load memories");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [userId, refreshKey]);

  if (!userId) {
    return <div className="text-sm text-slate-400 p-4">Enter a user ID to see memories</div>;
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      {error && (
        <div className="bg-red-50 text-red-700 text-sm rounded-md p-2 mb-3">{error}</div>
      )}
      <MemoryStatsRow stats={stats} />
      <MemoryDecayChart memories={memories} />
      {memories.length === 0 ? (
        <div className="text-sm text-slate-400">No memories yet</div>
      ) : (
        memories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)
      )}
    </div>
  );
}
