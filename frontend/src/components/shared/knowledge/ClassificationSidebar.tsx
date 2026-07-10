import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { RiMedicineBottleLine, RiFilePdf2Line } from "@remixicon/react"
interface ClassificationSidebarProps {
  status: 'review' | 'approved';
}

export function ClassificationSidebar({ status }: ClassificationSidebarProps) {
  return (
    <div className="w-[280px] lg:w-[320px] shrink-0 p-4 bg-zinc-50/50 border-l border-black/5 flex flex-col overflow-y-auto">
      <div className="bg-white rounded-md border border-black/10 shadow-sm flex flex-col overflow-hidden shrink-0">
        <div className="p-3 border-b border-black/5">
          <h2 className="text-sm font-medium text-zinc-950">Knowledge Classification</h2>
        </div>
        
        <div className="p-3.5 flex flex-col gap-4">
        {/* File Name */}
        <div>
          <label className="text-xs font-medium text-zinc-500 mb-1 block">File Name</label>
          <p className="text-sm text-zinc-950">ERHA Acne Spot Gel Protocol</p>
        </div>

        {/* Type */}
        <div>
          <label className="text-xs font-medium text-zinc-500 mb-1 block">Type</label>
          <div className="flex items-center gap-1.5 text-blue-600">
            <RiMedicineBottleLine className="size-4" />
            <span className="text-sm font-medium">Product</span>
          </div>
        </div>

        {/* Source */}
        <div>
          <label className="text-xs font-medium text-zinc-500 mb-1 block">Source</label>
          <div className="flex items-center gap-1.5 text-red-500">
            <RiFilePdf2Line className="size-4" />
            <span className="text-sm font-medium">PDF</span>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-zinc-500 mb-1 block">Status</label>
          {status === 'review' ? (
            <Badge variant="secondary" className="bg-orange-50 text-orange-700 hover:bg-orange-50 border-none">
              On review
            </Badge>
          ) : (
            <Badge variant="secondary" className="bg-green-50 text-green-700 hover:bg-green-50 border-none">
              Approved
            </Badge>
          )}
        </div>

        {/* AI Confidence Score */}
        <div className="pt-2">
          <label className="text-xs font-medium text-zinc-500 mb-2 block">AI Confidence Score</label>
          <div className="bg-blue-50/50 rounded-md p-2.5">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs text-zinc-950">Text Accuracy</span>
              <span className="text-xs font-medium text-blue-600">95%</span>
            </div>
            <Progress value={95} className="h-2 bg-blue-100" />
          </div>
        </div>
      </div>
    </div>
  </div>
  )
}
