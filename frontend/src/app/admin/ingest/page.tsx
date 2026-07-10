
import { PromptInput } from "@/components/shared/prompt-input";
import { 
  RiRobot2Line, 
  RiMedicineBottleLine, 
  RiSyringeLine,
  RiFileTextLine
} from "@remixicon/react";

export default function IngestPage() {
  return (
    <div className="flex flex-col max-w-2xl mx-auto min-h-full w-full pt-10 pb-10 px-4">
      {/* Header */}
      <div className="flex flex-col items-center text-center space-y-2 mb-8">
        <div className="flex aspect-square size-12 items-center justify-center rounded-md bg-blue-50 text-blue-500">
          <RiRobot2Line className="size-6" />
        </div>
        <div className="space-y-1">
          <h1 className="text-lg font-semibold tracking-tight text-zinc-950">
            Expand our clinical knowledge today
          </h1>
          <p className="text-[13px] text-zinc-500 max-w-95 leading-relaxed">
            Ingesting documenst to train the ai erha knowledge with product, treatment, and promotional brochure
          </p>
        </div>
      </div>
      {/* Shortcuts */}
      <div className="grid grid-cols-2 gap-3 w-full mb-4 shrink-0">
        <button className="flex flex-col items-start p-2.5 text-left rounded-md border border-border hover:border-zinc-300 hover:bg-zinc-50 transition-colors">
          <RiMedicineBottleLine className="size-4 text-zinc-950 mb-1.5" />
          <h3 className="font-semibold text-xs text-zinc-950 mb-0.5">Product Knowledge</h3>
          <p className="text-[11px] leading-tight text-zinc-500">Can you suggest a product for this condition...</p>
        </button>
        <button className="flex flex-col items-start p-2.5 text-left rounded-md border border-border hover:border-zinc-300 hover:bg-zinc-50 transition-colors">
          <RiSyringeLine className="size-4 text-zinc-950 mb-1.5" />
          <h3 className="font-semibold text-xs text-zinc-950 mb-0.5">Treatment Recomendation</h3>
          <p className="text-[11px] leading-tight text-zinc-500">Could you recommend a treatment for this condition...</p>
        </button>
      </div>

      {/* Prompt Input */}
      <div className="shrink-0 mt-4 flex flex-col items-center">
        <div className="w-full">
          <PromptInput minRows={3} />
        </div>
        <div className="mt-3 px-4 w-fit mx-auto border border-zinc-200 rounded-xl p-2.5 flex items-center justify-center text-xs text-zinc-500 bg-white">
          <RiFileTextLine className="size-3 mr-2 text-zinc-400" />
          File format including PDF, docx, excel, image
        </div>
      </div>
    </div>
  );
}
