"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { RiAddLine, RiImageAddLine } from "@remixicon/react"

export function AddBranchSheet() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <Button 
        className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 font-medium"
        onClick={() => setOpen(true)}
      >
        <RiAddLine className="size-4 mr-2" />
        Add New Branch
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent className="sm:max-w-100 w-full p-0 flex flex-col gap-0 border-l border-black-50 bg-white">
          <SheetHeader className="p-4 border-b border-black-50">
          <SheetTitle className="text-base font-medium text-black-500 text-left">Add New Branch</SheetTitle>
        </SheetHeader>
        
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
          {/* Branch Picture */}
          <div className="flex flex-col gap-2">
            <Label className="text-sm font-normal text-black-500">Branch Picture</Label>
            <div className="border border-dashed border-black-100 rounded-lg bg-zinc-50 p-6 flex flex-col items-center justify-center text-center gap-3">
              <div className="size-10 rounded-full bg-white flex items-center justify-center border border-black-50 shadow-sm">
                <RiImageAddLine className="size-5 text-black-300" />
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-sm">
                  <span className="font-medium text-black-500">Drag & Drop or </span>
                  <span className="font-medium text-blue-600 cursor-pointer hover:underline">Choose File</span>
                </p>
                <p className="text-xs text-black-300">Maximum file size: 5 MB</p>
                <p className="text-xs text-black-300">Format file: .jpg, .jpeg, .png</p>
              </div>
            </div>
          </div>

          {/* Name */}
          <div className="flex flex-col gap-2">
            <Label className="text-sm font-normal text-black-500">Name</Label>
            <Input placeholder="Erha Gunung Kidul" className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" />
          </div>

          {/* Location */}
          <div className="flex flex-col gap-2">
            <Label className="text-sm font-normal text-black-500">Location</Label>
            <Textarea 
              placeholder="Pakuwon Mall Jogja, Lantai 1..." 
              className="min-h-30 rounded-lg border-black-50 bg-white text-sm text-black-500 resize-none p-3" 
            />
          </div>

          {/* Latitude & Longitude */}
          <div className="flex items-center gap-4">
            <div className="flex flex-col gap-2 flex-1">
              <Label className="text-sm font-normal text-black-500">Latitude</Label>
              <Input placeholder="7°45'32.2&quot;S" className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" />
            </div>
            <div className="flex flex-col gap-2 flex-1">
              <Label className="text-sm font-normal text-black-500">Longitude</Label>
              <Input placeholder="110°23'57.3&quot;E" className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500" />
            </div>
          </div>

          {/* Tokens */}
          <div className="flex flex-col gap-2">
            <Label className="text-sm font-normal text-black-500">Tokens</Label>
            <div className="relative">
              <Input type="number" placeholder="1000" className="h-10 rounded-lg border-black-50 bg-white text-sm text-black-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-black-200 pointer-events-none">
                per month
              </span>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-black-50 flex justify-end gap-3 bg-white">
          <Button 
            variant="outline" 
            className="border-blue-500 text-blue-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg font-medium px-5 shadow-none" 
            onClick={() => setOpen(false)}
          >
            Cancel
          </Button>
          <Button 
            disabled 
            className="bg-black-50 text-black-200 rounded-lg font-medium px-5 shadow-none disabled:opacity-100"
          >
            Add Branch
          </Button>
        </div>
      </SheetContent>
    </Sheet>
    </>
  )
}
