import { RiCalendarLine, RiMessageAi3Line } from "@remixicon/react"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ChatHistoryItem } from "@/dummy/chat-history"

export function ChatHistoryCard({ item }: { item: ChatHistoryItem }) {
  return (
    <Card className="p-4 flex flex-col gap-3">
      <h3 className="text-sm font-medium text-foreground line-clamp-2">
        {item.query}
      </h3>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <RiCalendarLine className="size-3.5" />
          <span>{item.date}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <RiMessageAi3Line className="size-3.5" />
          <span>{item.messages}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Avatar className="size-4">
            <AvatarFallback className="text-[8px] bg-primary/10 text-primary">
              {item.doctor
                .replace("Dr. ", "")
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </AvatarFallback>
          </Avatar>
          <span>{item.doctor}</span>
        </div>
      </div>
    </Card>
  )
}
