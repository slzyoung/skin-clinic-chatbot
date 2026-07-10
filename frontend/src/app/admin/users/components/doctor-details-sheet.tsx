"use client"

import { RiEdit2Line, RiSettings3Line } from "@remixicon/react"
import { useState } from "react"
import Image from "next/image"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Doctor } from "@/dummy/users"
import { DoctorManageBranchDialog } from "./doctor-manage-branch-dialog"
import { DoctorManageKnowledgeDialog } from "./doctor-manage-knowledge-dialog"
import { DoctorAdjustLimitDialog } from "./doctor-adjust-limit-dialog"

export function DoctorDetailsSheet({
  isOpen,
  onOpenChange,
  doctor,
}: {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  doctor: Doctor | null
}) {
  const [isManageBranchOpen, setIsManageBranchOpen] = useState(false)
  const [isManageKnowledgeOpen, setIsManageKnowledgeOpen] = useState(false)
  const [isAdjustLimitOpen, setIsAdjustLimitOpen] = useState(false)

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-100 p-0 flex flex-col h-full bg-white gap-0">
        <SheetHeader className="p-4 border-b flex flex-row items-center">
          <SheetTitle className="text-base font-medium">Doctor Information</SheetTitle>
        </SheetHeader>
        
        {doctor && (
          <>
            <div className="flex-1 overflow-y-auto pb-6">
              <div className="flex flex-col pb-4">
                  {/* Profile Cover Image */}
                  <div className="relative h-65 w-full bg-gray-100 overflow-hidden shrink-0">
                    <Image 
                      src="/placeholder.svg" 
                      alt={doctor.name} 
                      fill
                      className="object-cover"
                    />
                    <div className="absolute top-4 right-4 z-10">
                      <Button 
                        variant="outline" 
                        className="bg-white/80 backdrop-blur-sm border-gray-200 text-gray-700 hover:bg-white hover:text-gray-900 px-3 py-0 rounded-lg shadow-none"
                      >
                        <RiEdit2Line className="size-4 mr-2" />
                        Edit Profile
                      </Button>
                    </div>
                  </div>

                  {/* Details Section */}
                  <div className="flex flex-col gap-4 px-6 py-4">
                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Name</span>
                      <span className="text-sm text-gray-900">{doctor.name}</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Role</span>
                      <span className="text-sm text-gray-900">Doctor</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Email</span>
                      <span className="text-sm text-gray-900">{doctor.name.replace("Dr. ", "")}@gmail.com</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between items-center">
                        <div className="flex flex-col gap-2">
                          <span className="text-sm text-gray-500">Tokens Remaining</span>
                          <span className="text-sm text-gray-900">{doctor.tokensLeft} / {doctor.maxTokens} tokens</span>
                        </div>
                        <Button variant="outline" className="" onClick={() => setIsAdjustLimitOpen(true)}>
                          <RiEdit2Line className="mr-2 h-4 w-4" />
                          Adjust Limit
                        </Button>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 pt-2">
                      <span className="text-sm text-gray-500">Branch</span>
                      <div className="border border-gray-200 rounded-md p-3 flex flex-col gap-3">
                        <div className="flex items-center gap-3">
                          <Avatar className="h-10 w-10 rounded-md after:rounded-md shrink-0">
                            <AvatarImage src="/mini-placeholder.svg" className="object-cover rounded-md" />
                            <AvatarFallback className="rounded-md"></AvatarFallback>
                          </Avatar>
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-gray-900">{doctor.branch}</span>
                            <span className="text-xs text-gray-500">Pakuwon Mall Jogja, Lantai 1, Kaliwaru, Condongcatur, Kec. Depok, Kabupaten Sleman, Daerah Istimewa Yogyakarta 55281</span>
                          </div>
                        </div>
                      </div>
                      <Button variant="outline" className="w-full mt-2 rounded-md" onClick={() => setIsManageBranchOpen(true)}>
                        <RiSettings3Line className="mr-2 h-4 w-4" />
                        Manage Branch
                      </Button>
                    </div>

                    <div className="flex flex-col gap-2 pt-2">
                      <span className="text-sm text-gray-500">Knowledge Base</span>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary" className="bg-gray-100 text-gray-900">Acne Care</Badge>
                        <Badge variant="secondary" className="bg-gray-100 text-gray-900">Anti Aging</Badge>
                        <Badge variant="secondary" className="bg-gray-100 text-gray-900">Dark Spot</Badge>
                      </div>
                      <Button variant="outline" className="w-full mt-2 rounded-md" onClick={() => setIsManageKnowledgeOpen(true)}>
                        <RiSettings3Line className="mr-2 h-4 w-4" />
                        Manage Knowledge Base
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            
            <div className="p-4 border-t border-gray-200 bg-white flex justify-start gap-3">
              <Button variant="outline" className="bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:text-gray-900" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </div>

            <DoctorManageBranchDialog 
              isOpen={isManageBranchOpen} 
              onOpenChange={setIsManageBranchOpen} 
            />

            <DoctorManageKnowledgeDialog 
              isOpen={isManageKnowledgeOpen} 
              onOpenChange={setIsManageKnowledgeOpen} 
            />

            <DoctorAdjustLimitDialog 
              isOpen={isAdjustLimitOpen} 
              onOpenChange={setIsAdjustLimitOpen} 
              doctor={doctor}
            />
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
