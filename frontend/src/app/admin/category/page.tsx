"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { RiSearchLine, RiAddLine, RiEdit2Line, RiDeleteBinLine } from "@remixicon/react"
import { CategoryDialog } from "./components/category-dialog"

const CATEGORIES = [
  { id: "1", name: "Acne Care" },
  { id: "2", name: "Anti Aging" },
  { id: "3", name: "Dark Spot" },
  { id: "4", name: "Psoriasis Care" },
  { id: "5", name: "Scar Treatment" },
  { id: "6", name: "Wound Healing" },
]

export default function CategoriesPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<"add" | "edit">("add")
  const [selectedCategory, setSelectedCategory] = useState<typeof CATEGORIES[0] | null>(null)

  const handleAddCategory = () => {
    setDialogMode("add")
    setSelectedCategory(null)
    setIsDialogOpen(true)
  }

  const handleEditCategory = (category: typeof CATEGORIES[0]) => {
    setDialogMode("edit")
    setSelectedCategory(category)
    setIsDialogOpen(true)
  }

  return (
    <div className="p-6 flex flex-col gap-6 h-full">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-gray-900">Category</h1>
        <p className="text-sm text-gray-500">
          Explore a wide array of categorized products.
        </p>
      </div>

      <div className="flex flex-col">
        {/* Actions */}
        <div className="flex items-center justify-between mb-4">
          <div className="relative flex items-center w-80">
            <RiSearchLine className="absolute left-2.5 w-4 h-4 text-gray-400" />
            <Input 
              placeholder="Search for category" 
              className="pl-8 bg-white"
            />
          </div>
          <Button className="bg-blue-500 hover:bg-blue-600" onClick={handleAddCategory}>
            <RiAddLine className="mr-2 h-4 w-4" />
            Add Category
          </Button>
        </div>

        {/* Table */}
        <div className="border border-gray-100 rounded-md bg-white overflow-hidden">
          <Table className="[&_tr]:border-gray-100">
            <TableHeader className="bg-gray-50/50">
              <TableRow>
                <TableHead className="w-[35%]">Category</TableHead>
                <TableHead className="w-50 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {CATEGORIES.map((category) => (
                <TableRow key={category.id}>
                  <TableCell>
                    <Badge 
                      variant="secondary" 
                      className="bg-black-50 text-black-500 hover:bg-black-50/80"
                    >
                      {category.name}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button 
                        variant="outline" 
                        size="md"
                        className="bg-white border-black-50 text-black-500 hover:bg-gray-50 font-medium"
                        onClick={() => handleEditCategory(category)}
                      >
                        <RiEdit2Line className="size-4 mr-1.5" />
                        Edit
                      </Button>
                      <Button 
                        variant="outline" 
                        size="md"
                        className="bg-white border-black-50 text-black-500 hover:bg-gray-50 font-medium"
                      >
                        <RiDeleteBinLine className="size-4 mr-1.5" />
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <CategoryDialog 
        isOpen={isDialogOpen} 
        onOpenChange={setIsDialogOpen} 
        mode={dialogMode} 
        category={selectedCategory} 
      />
    </div>
  )
}
