import { ChatPreview } from "@/components/shared/knowledge/ChatPreview"
import { ClassificationSidebar } from "@/components/shared/knowledge/ClassificationSidebar"
import { ActionBar } from "./components/ActionBar"

export default function IngestReviewPage() {
  return (
    <div className="flex flex-col absolute inset-0">
      {/* Title Header */}
      <div className="px-6 py-3 border-b border-black/10 bg-white shrink-0">
        <h1 className="text-sm font-semibold text-zinc-950">
          ERHA Acne Spot Gel Protocol
        </h1>
      </div>
      
      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column (Chat / Preview) */}
        <ChatPreview />
        
        {/* Right Column (Classification) */}
        <ClassificationSidebar status="review" />
      </div>

      {/* Action Bar */}
      <ActionBar />
    </div>
  )
}
