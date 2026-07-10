"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RiCheckLine } from "@remixicon/react";

export function DoctorManageKnowledgeDialog({
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
            Manage Knowledge
          </DialogTitle>
        </DialogHeader>

        <div className="p-4 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
          {/* List of knowledge */}
          <div className="flex flex-col gap-3">
            {/* Selected items */}
            <div className="border border-blue-500 bg-blue-50 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="knowledge-1"
                  defaultChecked
                  className="data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
                />
                <span className="text-sm font-medium text-gray-900">
                  Acne Care
                </span>
              </div>
            </div>

            <div className="border border-blue-500 bg-blue-50 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="knowledge-2"
                  defaultChecked
                  className="data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
                />
                <span className="text-sm font-medium text-gray-900">
                  Anti Aging
                </span>
              </div>
            </div>

            <div className="border border-blue-500 bg-blue-50 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="knowledge-3"
                  defaultChecked
                  className="data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
                />
                <span className="text-sm font-medium text-gray-900">
                  Dark Spot
                </span>
              </div>
            </div>

            {/* Unselected items */}
            <div className="border border-gray-200 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox id="knowledge-4" />
                <span className="text-sm font-medium text-gray-900">
                  Psoriasis Care
                </span>
              </div>
            </div>

            <div className="border border-gray-200 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox id="knowledge-5" />
                <span className="text-sm font-medium text-gray-900">
                  Scar Treatment
                </span>
              </div>
            </div>

            <div className="border border-gray-200 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox id="knowledge-6" />
                <span className="text-sm font-medium text-gray-900">
                  Wound Healing
                </span>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 text-sm text-yellow-900">
            Choose one or more knowledge to assign to the doctor, ensuring the
            chatbot only responds with relevant information.
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 flex justify-end">
          <Button
            variant="outline"
            className="bg-gray-100 text-gray-500 border-0 hover:bg-gray-200 hover:text-gray-700 px-6 rounded-md"
            onClick={() => onOpenChange(false)}
          >
            <RiCheckLine className="mr-2 h-4 w-4" />
            Save Knowledge
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
