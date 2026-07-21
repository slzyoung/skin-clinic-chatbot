"use client";

import { ChatPreview } from "@/components/shared/knowledge/ChatPreview"
import { ClassificationSidebar } from "@/components/shared/knowledge/ClassificationSidebar"
import { ActionBar } from "./components/ActionBar"
import { use } from "react"
import { useKnowledgeDetail } from "../../knowledge/hooks/use-knowledge"

export default function IngestReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const unwrappedParams = use(params)
  const id = unwrappedParams.id
  const { data, isLoading, error } = useKnowledgeDetail(id)

  if (isLoading) {
    return <div className="flex items-center justify-center h-full">Loading...</div>
  }

  if (error || !data) {
    return <div className="flex items-center justify-center h-full text-red-500">Error loading document details</div>
  }

  return (
    <div className="flex flex-col absolute inset-0">
      {/* Title Header */}
      <div className="px-6 py-3 border-b border-black/10 bg-white shrink-0">
        <h1 className="text-sm font-semibold text-zinc-950">
          {data.title}
        </h1>
      </div>
      
      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column (Chat / Preview) */}
        <ChatPreview knowledgeId={data.id} knowledgeStatus={data.status} />
        
        {/* Right Column (Classification) */}
        <ClassificationSidebar knowledge={data} />
      </div>

      {/* Action Bar */}
      <ActionBar />
    </div>
  )
}
