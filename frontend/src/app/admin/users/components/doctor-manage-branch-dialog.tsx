"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RiCheckLine } from "@remixicon/react";
import { mockBranches } from "@/dummy/branches";

export function DoctorManageBranchDialog({
  isOpen,
  onOpenChange,
}: {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md p-0 flex flex-col gap-0 rounded-md overflow-hidden bg-white border-0">
        <DialogHeader className="p-4 border-b border-gray-100 flex flex-row items-center justify-between">
          <DialogTitle className="text-base font-medium text-gray-900">
            Manage Branches
          </DialogTitle>
        </DialogHeader>

        <div className="p-4 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
          {/* List of branches */}
          <div className="flex flex-col gap-3">
            {mockBranches.map((branch) => {
              const isSelected = branch.id === "branch-2";
              return (
                <div 
                  key={branch.id} 
                  className={
                    isSelected 
                      ? "border border-blue-500 bg-blue-50 rounded-md p-3 flex items-center justify-between"
                      : "border border-gray-200 rounded-md p-3 flex items-center justify-between"
                  }
                >
                  <div className="flex items-center gap-3">
                    <Checkbox
                      id={branch.id}
                      defaultChecked={isSelected}
                      className="data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
                    />
                    <Avatar className="h-10 w-10 rounded-md after:rounded-md shrink-0">
                      <AvatarImage src="/mini-placeholder.svg" className="object-cover rounded-md" />
                      <AvatarFallback className="rounded-md"></AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-900">
                        {branch.name}
                      </span>
                      <span className="text-xs text-gray-500">
                        {branch.address}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 text-sm text-yellow-900">
            Choose one or more branch to assign to the doctor, allowing them to
            utilize the chatbot in each branch.
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 flex justify-end">
          <Button
            variant="outline"
            className="bg-gray-100 text-gray-500 border-0 hover:bg-gray-200 hover:text-gray-700 px-6 rounded-md"
            onClick={() => onOpenChange(false)}
          >
            <RiCheckLine className="mr-2 h-4 w-4" />
            Save Branches
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
