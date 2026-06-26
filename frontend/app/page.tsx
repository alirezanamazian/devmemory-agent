"use client";

import { useEffect, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { MemoryPanel } from "@/components/MemoryPanel";

const STORAGE_KEY = "devmemory_user_id";

export default function Page() {
  const [userId, setUserId] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setUserId(stored);
    }
  }, []);

  function handleUserIdChange(value: string) {
    setUserId(value);
    window.localStorage.setItem(STORAGE_KEY, value);
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="border-b bg-white px-4 py-2 flex items-center gap-3">
        <span className="font-semibold">DevMemory</span>
        <input
          className="border rounded-md px-2 py-1 text-sm"
          placeholder="user_id"
          value={userId}
          onChange={(e) => handleUserIdChange(e.target.value)}
        />
      </header>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 border-r bg-slate-50">
          <ChatPanel userId={userId} onMessageSent={() => setRefreshKey((k) => k + 1)} />
        </div>
        <div className="w-[380px] bg-slate-100">
          <MemoryPanel userId={userId} refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  );
}
