import { ChatPreview } from "@/components/shared/knowledge/ChatPreview"
import { ClassificationSidebar } from "@/components/shared/knowledge/ClassificationSidebar"
import { Button } from "@/components/ui/button"
import { RiArrowLeftLine, RiEdit2Line, RiDeleteBin7Line } from "@remixicon/react"
import Link from "next/link"

export default function KnowledgeDetailPage() {
  return (
    <div className="flex flex-col absolute inset-0">
      {/* Title Header with Actions */}
      <div className="px-6 py-3 border-b border-black/10 bg-white shrink-0 flex items-center justify-between">
        <Link href="/knowledge" className="flex items-center gap-2 text-zinc-950 hover:text-zinc-700 transition-colors">
          <RiArrowLeftLine className="size-4" />
          <span className="text-sm font-semibold">Back to Knowledge Base</span>
        </Link>

        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200">
            <RiDeleteBin7Line className="size-4" />
            Delete Knowledge
          </Button>
          <Button variant="outline" className="gap-2 text-zinc-950">
            <RiEdit2Line className="size-4" />
            Edit Knowledge
          </Button>
        </div>
      </div>
      
      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column (Chat / Preview) */}
        <ChatPreview />
        
        {/* Right Column (Classification) */}
        <ClassificationSidebar status="approved" />
      </div>
    </div>
  )
}
