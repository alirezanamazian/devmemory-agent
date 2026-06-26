"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteMemory, fetchMemories, fetchMemoryStats, MemoryResponse, MemoryStats } from "@/lib/api";
import { MemoryStatsRow } from "@/components/MemoryStatsRow";
import { MemoryDecayChart } from "@/components/MemoryDecayChart";
import { MemoryCard } from "@/components/MemoryCard";

export function MemoryPanel({ userId, refreshKey }: { userId: string; refreshKey: number }) {
  const [memories, setMemories] = useState<MemoryResponse[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localRefresh, setLocalRefresh] = useState(0);

  const load = useCallback(
    async (cancelledRef: { cancelled: boolean }) => {
      try {
        const [memList, statsResult] = await Promise.all([
          fetchMemories(userId),
          fetchMemoryStats(userId),
        ]);
        if (!cancelledRef.cancelled) {
          setMemories(memList);
          setStats(statsResult);
          setError(null);
        }
      } catch (err) {
        if (!cancelledRef.cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load memories");
        }
      }
    },
    [userId]
  );

  useEffect(() => {
    if (!userId) {
      return;
    }
    const cancelledRef = { cancelled: false };
    load(cancelledRef);
    return () => {
      cancelledRef.cancelled = true;
    };
  }, [userId, refreshKey, localRefresh, load]);

  async function handleDelete(memoryId: string) {
    try {
      await deleteMemory(userId, memoryId);
      setLocalRefresh((k) => k + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete memory");
    }
  }

  if (!userId) {
    return <div className="text-sm text-slate-400 p-4">Enter a user ID to see memories</div>;
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      {error && (
        <div className="bg-red-50 text-red-700 text-sm rounded-md p-2 mb-3">{error}</div>
      )}

      <h2 className="text-xs font-semibold uppercase text-slate-500 mb-2">Memory Stats</h2>
      <MemoryStatsRow stats={stats} />

      <h2 className="text-xs font-semibold uppercase text-slate-500 mb-2">
        Importance Decay (live, recalculated each render)
      </h2>
      <MemoryDecayChart memories={memories} />

      <h2 className="text-xs font-semibold uppercase text-slate-500 mb-2">
        All Memories ({memories.length})
      </h2>
      {memories.length === 0 ? (
        <div className="text-sm text-slate-400">No memories yet</div>
      ) : (
        memories.map((memory) => (
          <MemoryCard key={memory.id} memory={memory} onDelete={handleDelete} />
        ))
      )}
    </div>
  );
}
