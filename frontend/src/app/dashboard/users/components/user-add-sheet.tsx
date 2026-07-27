import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { RiEyeLine, RiImageAddLine } from "@remixicon/react"
import { useState } from "react"
import { useCreateStaff } from "../hooks/use-users"

export function UserAddSheet({
  isOpen,
  onOpenChange,
}: {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("")
  
  const createStaff = useCreateStaff()

  const handleAddUser = () => {
    if (!name || !email) return;
    
    createStaff.mutate({
      name,
      email,
      password: password || "password123",
      roles: role === "admin" ? ["Admin"] : ["Staff"],
    }, {
      onSuccess: () => onOpenChange(false)
    })
  }

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md p-0 flex flex-col h-full bg-white">
        <SheetHeader className="p-4 border-b h-15 flex justify-center">
          <SheetTitle className="text-base font-semibold text-gray-900 flex justify-between items-center w-full">
            Add New User
          </SheetTitle>
        </SheetHeader>
        
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label className="text-sm font-medium text-gray-900">Profile Picture</Label>
              <div className="border border-gray-200 rounded-md p-4 flex flex-col items-center justify-center text-center">
                <div className="h-8 w-8 mb-2 flex items-center justify-center text-gray-400">
                  <RiImageAddLine className="h-5 w-5" />
                </div>
                <div className="flex gap-1 text-sm">
                  <span className="font-medium text-gray-900">Drag & Drop or</span>
                  <span className="font-medium text-blue-500 cursor-pointer">Choose File</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Maximum file size: 5 MB</p>
                <p className="text-xs text-gray-500">Format file: .jpg, .jpeg, .png</p>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="name" className="text-sm font-medium text-gray-900">Name</Label>
              <div className="relative">
                <Input 
                  id="name" 
                  placeholder="John Doe" 
                  className="border-gray-200 bg-white focus-visible:ring-blue-500" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="role" className="text-sm font-medium text-gray-900">Role</Label>
              <Select value={role} onValueChange={(val) => setRole(val ?? "")}>
                <SelectTrigger className="w-full border-gray-200 bg-white text-gray-700">
                  <SelectValue placeholder="Select one role" />
                </SelectTrigger>
                <SelectContent alignItemWithTrigger={false} sideOffset={4}>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="dept_functional">Dept Functional</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-gray-900">Email</Label>
              <div className="relative">
                <Input 
                  id="email" 
                  type="email" 
                  placeholder="example@gmail.com" 
                  className="border-gray-200 bg-white focus-visible:ring-blue-500" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-gray-900">Password</Label>
              <div className="relative">
                <Input 
                  id="password" 
                  type="password" 
                  placeholder="********" 
                  className="border-gray-200 bg-white focus-visible:ring-blue-500 pr-10" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <Button variant="ghost" size="icon" className="absolute right-0 top-0 text-gray-500 hover:text-gray-700">
                  <RiEyeLine className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-4 border-t border-gray-200 bg-white flex justify-end gap-3">
          <Button variant="outline" className="bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:text-gray-900" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button 
            className="bg-blue-600 text-white hover:bg-blue-700"
            onClick={handleAddUser}
            disabled={createStaff.isPending}
          >
            {createStaff.isPending ? "Adding..." : "Add User"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
