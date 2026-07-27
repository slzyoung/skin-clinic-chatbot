import { RiUserLine, RiArrowDownSLine } from "@remixicon/react"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ChatFilter({ doctors = [] }: { doctors?: string[] }) {
  return (
    <div className="flex items-center gap-3">
      <DropdownMenu>
        <DropdownMenuTrigger className={cn(buttonVariants({ variant: "outline" }), "flex items-center justify-between w-55 font-normal")}>
          <div className="flex items-center gap-2">
            <RiUserLine className="w-4 h-4 text-gray-700" />
            <span>Filtered by Doctor</span>
          </div>
          <RiArrowDownSLine className="w-4 h-4 text-gray-400" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-55">
          <DropdownMenuItem>All Doctors</DropdownMenuItem>
          {doctors.map(
            (doctor) => (
              <DropdownMenuItem key={doctor}>
                {doctor}
              </DropdownMenuItem>
            )
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
