"use client";

import { useState } from "react";
import { sendChatMessage } from "@/lib/api";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  memoriesUsed?: number;
}

export function ChatPanel({ userId, onMessageSent }: { userId: string; onMessageSent: () => void }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSend() {
    if (!input.trim() || !userId || sending) {
      return;
    }
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const response = await sendChatMessage(userId, userMessage);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
          memoriesUsed: response.memories_used.length,
        },
      ]);
      onMessageSent();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col h-full p-4">
      <div className="flex-1 overflow-y-auto mb-3 space-y-2">
        {messages.map((message, index) => (
          <div
            key={index}
            className={
              message.role === "user"
                ? "text-right"
                : "text-left"
            }
          >
            <div
              className={
                message.role === "user"
                  ? "inline-block bg-sky-600 text-white rounded-lg px-3 py-2 max-w-[80%]"
                  : "inline-block bg-white border rounded-lg px-3 py-2 max-w-[80%]"
              }
            >
              {message.content}
              {message.memoriesUsed ? (
                <div className="text-xs text-slate-400 mt-1">used {message.memoriesUsed} memories</div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      {error && <div className="bg-red-50 text-red-700 text-sm rounded-md p-2 mb-2">{error}</div>}
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded-md px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
          placeholder="Ask DevMemory..."
          disabled={!userId}
        />
        <button
          className="bg-sky-600 text-white rounded-md px-4 py-2 disabled:opacity-50"
          onClick={handleSend}
          disabled={!userId || sending}
        >
          Send
        </button>
      </div>
    </div>
  );
}
