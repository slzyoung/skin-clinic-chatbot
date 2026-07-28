import { RiCalendarLine, RiMessageAi3Line, RiHospitalLine, RiUser3Line } from "@remixicon/react"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import type { ChatHistoryResponse } from "../api/types"

export function ChatHistoryCard({ item }: { item: ChatHistoryResponse }) {
  const formattedDate = new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit'
  }).format(new Date(item.created_at))

  return (
    <Card className="p-4 flex flex-col gap-3">
      <h3 className="text-sm font-medium text-foreground line-clamp-2">
        {item.query || "Empty Chat"}
      </h3>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <RiCalendarLine className="size-3.5" />
          <span>{formattedDate}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <RiMessageAi3Line className="size-3.5" />
          <span>{item.messages}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Avatar className="size-4">
            <AvatarFallback className="bg-primary/10 text-primary">
              <RiUser3Line className="size-2.5" />
            </AvatarFallback>
          </Avatar>
          <span>{item.doctor}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <RiHospitalLine className="size-3.5" />
          <span>{item.branch}</span>
        </div>
      </div>
    </Card>
  )
}
