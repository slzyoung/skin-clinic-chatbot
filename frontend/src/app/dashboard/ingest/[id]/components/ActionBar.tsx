import { Button } from "@/components/ui/button"
import { RiInformationLine, RiFileCheckLine } from "@remixicon/react"

export function ActionBar() {
  return (
    <div className="flex items-center justify-between p-3 border-t border-black/10 bg-background mt-auto shrink-0">
      <div className="flex items-center gap-2 pl-2">
        <RiInformationLine className="size-5 text-zinc-500" />
        <span className="text-sm text-zinc-500">
          The changes will be implemented here
        </span>
      </div>
      <Button className="bg-blue-600 hover:bg-blue-700 text-white gap-2" >
        <RiFileCheckLine className="size-4" />
        Approve Knowledge
      </Button>
    </div>
  )
}
