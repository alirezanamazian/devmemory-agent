import { MemoryResponse } from "@/lib/api";
import { calculateCurrentImportance } from "@/lib/decay";

export function MemoryCard({ memory }: { memory: MemoryResponse }) {
  const effectiveImportance = calculateCurrentImportance({
    importanceScore: memory.importance_score,
    decayRate: memory.decay_rate,
    lastAccessed: memory.last_accessed,
    accessCount: memory.access_count,
  });

  return (
    <div className="border rounded-md p-3 mb-2 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium uppercase text-slate-500">{memory.memory_type}</span>
        <span className="text-xs text-slate-400">accessed {memory.access_count}x</span>
      </div>
      <p className="text-sm truncate" title={memory.content}>
        {memory.content}
      </p>
      <div className="mt-2 h-1.5 bg-slate-100 rounded">
        <div
          className="h-1.5 bg-emerald-500 rounded"
          style={{ width: `${Math.round(effectiveImportance * 100)}%` }}
        />
      </div>
    </div>
  );
}
