"use client"

import { RiRobot2Line, RiUser3Line } from "@remixicon/react"
import { PromptInput } from "@/components/shared/prompt-input"
import { ChatEndSessionDialog } from "./components/chat-end-session-dialog"
import { ChatSummaryBubble } from "./components/chat-summary-bubble"
import { ChatOutOfScopeBubble } from "./components/chat-out-of-scope-bubble"
import * as React from "react"
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
} from "@/components/ui/message-scroller"

export default function DoctorChatSessionPage() {
  const [showEndSession, setShowEndSession] = React.useState(true) // For preview

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden w-full max-w-3xl mx-auto relative">
      {/* Chat Messages */}
      <MessageScrollerProvider>
        <MessageScroller className="flex-1 w-full px-4 bg-white">
          <MessageScrollerViewport>
            <MessageScrollerContent className="gap-6 py-6 w-full">
              {/* User Text Bubble */}
              <MessageScrollerItem>
                <div className="flex items-start gap-3 mt-2 flex-row-reverse">
                  <div className="bg-zinc-100 rounded-md text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiUser3Line className="size-4" />
                  </div>
                  <div className="bg-blue-500 text-white p-3 rounded-md text-sm w-full leading-relaxed">
                    Buatkan rencana perawatan untuk pasien dengan dokumen yang telah saya sertakan
                  </div>
                </div>
              </MessageScrollerItem>

              {/* AI Assistant Blue Bubble */}
              <MessageScrollerItem>
                <div className="flex items-start gap-3">
                  <div className="bg-zinc-100 rounded-md text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiRobot2Line className="size-4" />
                  </div>
                  <div className="bg-blue-50 text-zinc-950 p-3 rounded-md text-sm w-full leading-relaxed">
                    <p className="mb-2">Tentu Dokter, berikut adalah rencana perawatan untuk pasien berdasarkan dokumen yang diberikan.</p>
                    <ul className="list-disc pl-4 space-y-1">
                      <li>Gunakan <strong>ERHA Acne Spot Gel</strong> pada area yang berjerawat 2x sehari.</li>
                      <li>Gunakan tabir surya di pagi hari sebelum beraktivitas.</li>
                      <li>Hindari memencet jerawat untuk mencegah infeksi sekunder.</li>
                    </ul>
                  </div>
                </div>
              </MessageScrollerItem>

              <MessageScrollerItem>
                <div className="flex items-start gap-3">
                  <div className="bg-zinc-100 rounded-md text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiRobot2Line className="size-4" />
                  </div>
                  <div className="bg-blue-50 text-zinc-950 p-3 rounded-md text-sm w-full leading-relaxed">
                    <p className="mb-2">Tentu Dokter, berikut adalah rencana perawatan untuk pasien berdasarkan dokumen yang diberikan.</p>
                    <ul className="list-disc pl-4 space-y-1">
                      <li>Gunakan <strong>ERHA Acne Spot Gel</strong> pada area yang berjerawat 2x sehari.</li>
                      <li>Gunakan tabir surya di pagi hari sebelum beraktivitas.</li>
                      <li>Hindari memencet jerawat untuk mencegah infeksi sekunder.</li>
                    </ul>
                  </div>
                </div>
              </MessageScrollerItem>

              <MessageScrollerItem>
                <div className="flex items-start gap-3">
                  <div className="bg-zinc-100 rounded-md text-zinc-950 flex items-center justify-center p-1.5 mt-0.5 shrink-0">
                    <RiRobot2Line className="size-4" />
                  </div>
                  <div className="bg-blue-50 text-zinc-950 p-3 rounded-md text-sm w-full leading-relaxed">
                    <p className="mb-2">Tentu Dokter, berikut adalah rencana perawatan untuk pasien berdasarkan dokumen yang diberikan.</p>
                    <ul className="list-disc pl-4 space-y-1">
                      <li>Gunakan <strong>ERHA Acne Spot Gel</strong> pada area yang berjerawat 2x sehari.</li>
                      <li>Gunakan tabir surya di pagi hari sebelum beraktivitas.</li>
                      <li>Hindari memencet jerawat untuk mencegah infeksi sekunder.</li>
                    </ul>
                  </div>
                </div>
              </MessageScrollerItem>

              {/* Out of Scope Warning Bubble (No file) */}
              <MessageScrollerItem>
                <ChatOutOfScopeBubble />
              </MessageScrollerItem>

              {/* Session Summary Bubble */}
              <MessageScrollerItem scrollAnchor>
                <ChatSummaryBubble 
                  file={{ name: "Profil_Hamdan_Zakirun_Naik", type: "PDF" }}
                  summaryText={`Based on your facial condition, the primary diagnosis is Acne Vulgaris Grade II – Moderate.\n\nTo support daily acne care, the recommended product is ERHA Acne Cleanser, a facial cleanser specially formulated for acne-prone skin, priced at Rp120.000 with 24 units currently in stock.\n\nFor further treatment, especially to help address dark acne marks or post-inflammatory hyperpigmentation, the recommended program is Acne Finale Dark Spot Program, available in two options:\n\nBasic Plan: Rp1.452.000\nAdvance Plan: Rp3.012.000`}
                />
              </MessageScrollerItem>
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      {/* Chat Input */}
      <div className="p-4 bg-white shrink-0 mt-auto w-full z-10 border-t border-zinc-100">
        <PromptInput 
          hideCategories 
          showAttachText 
          placeholder="Can you suggest a product for this condition..." 
        />
      </div>

      <ChatEndSessionDialog 
        open={showEndSession} 
        onOpenChange={setShowEndSession}
      />
    </div>
  )
}
