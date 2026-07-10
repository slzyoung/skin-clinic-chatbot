import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { RiCheckLine } from "@remixicon/react"

interface Category {
  id: string
  name: string
}

interface CategoryDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  mode: "add" | "edit"
  category?: Category | null
}

export function CategoryDialog({ isOpen, onOpenChange, mode, category }: CategoryDialogProps) {
  const isEdit = mode === "edit"
  const title = isEdit ? "Category" : "Add New Category"
  const buttonText = isEdit ? "Save Changes" : "Add Category"

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-120 p-0 overflow-hidden bg-white rounded-xl">
        <DialogHeader className="p-4 border-b border-gray-100">
          <DialogTitle className="text-base font-medium text-gray-900">{title}</DialogTitle>
        </DialogHeader>

        <div className="p-4 flex flex-col gap-4">
          {isEdit && category && (
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-gray-900">Display</label>
              <div>
                <Badge 
                  variant="secondary" 
                  className="bg-black-50 text-black-500"
                >
                  {category.name}
                </Badge>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-sm text-gray-900">Input Category Name</label>
            <div className="relative">
              <Input 
                defaultValue={isEdit ? category?.name : ""} 
                placeholder="Category Name" 
                className="w-full bg-white h-10"
              />
            </div>
          </div>
        </div>

        <DialogFooter className="p-4 border-t border-gray-100 sm:justify-end">
          <Button 
            className="bg-black-50 hover:bg-black-50/80 text-black-500 font-medium px-5" 
            onClick={() => onOpenChange(false)}
          >
            <RiCheckLine className="size-4 mr-2" />
            {buttonText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
