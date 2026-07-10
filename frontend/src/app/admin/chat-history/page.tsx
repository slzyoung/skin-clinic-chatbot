import React from "react"
import { RiSearchLine } from "@remixicon/react"
import { CHAT_HISTORY } from "@/dummy/chat-history"
import { ChatHistoryCard } from "./components/chat-history-card"
import { ChatFilter } from "./components/chat-filter"
import { Input } from "@/components/ui/input"

export default function ChatHistoryPage() {
  return (
    <div className="flex flex-col h-full gap-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-foreground">Chat History</h1>
        <p className="text-sm text-muted-foreground">
          View past chats with the AI chatbot easily.
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4">
        <div className="relative flex items-center w-full max-w-100">
          <RiSearchLine className="absolute left-2.5 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search chat sessions"
            className="pl-8 bg-white"
          />
        </div>
        <ChatFilter />
      </div>

      {/* List */}
      <div className="flex flex-col gap-4">
        {CHAT_HISTORY.map((item) => (
          <ChatHistoryCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  )
}
