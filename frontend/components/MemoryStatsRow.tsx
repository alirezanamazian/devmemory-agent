import { MemoryStats } from "@/lib/api";

export function MemoryStatsRow({ stats }: { stats: MemoryStats | null }) {
  if (!stats) {
    return null;
  }

  return (
    <div className="grid grid-cols-3 gap-2 mb-3">
      <div className="border rounded-md p-2 text-center bg-white">
        <div className="text-lg font-semibold">{stats.total_memories}</div>
        <div className="text-xs text-slate-500">total</div>
      </div>
      <div className="border rounded-md p-2 text-center bg-white">
        <div className="text-lg font-semibold">
          {stats.avg_importance !== null ? stats.avg_importance.toFixed(2) : "—"}
        </div>
        <div className="text-xs text-slate-500">avg importance</div>
      </div>
      <div className="border rounded-md p-2 text-center bg-white">
        <div className="text-lg font-semibold text-amber-600">{stats.memories_at_risk}</div>
        <div className="text-xs text-slate-500">at risk</div>
      </div>
    </div>
  );
}
