import { RiDeleteBinLine, RiEdit2Line } from "@remixicon/react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { UserResponse } from "../api/types"

export function UserStaffProfileSheet({
  isOpen,
  onOpenChange,
  staff,
}: {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  staff: UserResponse | null
}) {
  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-100 p-0 flex flex-col h-full bg-white gap-0">
        <SheetHeader className="p-4 border-b flex flex-row items-center">
          <SheetTitle className="text-base font-medium">User Profile</SheetTitle>
        </SheetHeader>
        
        {staff && (
          <>
            <div className="flex-1 overflow-y-auto pb-6">
              <div className="flex flex-col pb-4">
                  {/* Profile Cover Image */}
                  <div className="relative h-65 w-full bg-gray-100 overflow-hidden shrink-0">
                    <Image 
                      src="/placeholder.svg" 
                      alt={staff.name} 
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
                      <span className="text-sm text-gray-900">{staff.name}</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Role</span>
                      <span className="text-sm text-gray-900">{staff.roles && staff.roles.length > 0 ? staff.roles[0].name : "Staff"}</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Email</span>
                      <span className="text-sm text-gray-900">{staff.email}</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Password</span>
                      <span className="text-sm text-gray-900">********</span>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="text-sm text-gray-500">Date & Time Created</span>
                      <span className="text-sm text-gray-900">
                        {new Date(staff.created_at).toLocaleString("en-US", {
                          year: "numeric",
                          month: "numeric",
                          day: "numeric",
                          hour: "numeric",
                          minute: "numeric",
                          hour12: true
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            
            <div className="p-4 border-t border-gray-200 bg-white flex justify-start gap-3">
              <Button variant={"outline"} className="border-red-500 text-red-600 hover:bg-red-50 hover:text-red-700">
                <RiDeleteBinLine className="mr-2 h-4 w-4" />
                Delete User
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
