"use client"

import * as React from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { 
  RiDatabase2Line, 
  RiHistoryLine, 
  RiUser3Line, 
  RiSettings4Line, 
  RiRobot2Line,
  RiFileAddLine,
  RiFunctionLine,
  RiLogoutBoxRLine
} from "@remixicon/react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useLogout } from "@/app/login/hooks/use-logout"

const adminNav = [
  {
    title: "Knowledge Base",
    url: "/admin/knowledge",
    icon: RiDatabase2Line,
  },
  {
    title: "Chat History",
    url: "/admin/chat-history",
    icon: RiHistoryLine,
  },
  {
    title: "User",
    url: "/admin/users",
    icon: RiUser3Line,
  },
  {
    title: "Category",
    url: "/admin/category",
    icon: RiFunctionLine,
  },
  {
    title: "Configuration",
    url: "/admin/configuration",
    icon: RiSettings4Line,
  },
]

export function AdminSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()
  const { mutate: logout, isPending: isLoggingOut } = useLogout()
  
  return (
    <Sidebar collapsible="icon" {...props} className="border-r border-border">
      <SidebarHeader className="px-4 pt-4 pb-0 group-data-[collapsible=icon]:p-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/admin/ingest" />} className="hover:bg-transparent hover:text-inherit active:bg-transparent cursor-default p-0 group-data-[collapsible=icon]:justify-center">
              <div className="flex aspect-square size-10 group-data-[collapsible=icon]:size-8 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-500">
                <RiRobot2Line className="size-5 group-data-[collapsible=icon]:size-4" />
              </div>
              <div className="flex flex-col gap-1 leading-none ml-2 group-data-[collapsible=icon]:hidden">
                <span className="font-semibold text-blue-500 text-sm">ERHA</span>
                <span className="font-semibold text-blue-500 text-sm">Medical Assistant</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <div className="px-4 pt-12 pb-2 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:pt-8">
          <Button render={<Link href="/admin/ingest" />} nativeButton={false} className="w-full justify-center bg-blue-500 hover:bg-blue-600 text-white shadow-none h-10 px-3 rounded-md group-data-[collapsible=icon]:size-8 group-data-[collapsible=icon]:p-0 shrink-0">
            <RiFileAddLine className="mr-2 size-5 group-data-[collapsible=icon]:mr-0 group-data-[collapsible=icon]:size-4 shrink-0" />
            <span className="font-medium text-sm group-data-[collapsible=icon]:hidden">Ingest Document</span>
          </Button>
        </div>
        <SidebarMenu className="px-3 mt-2 space-y-1 group-data-[collapsible=icon]:px-2">
          {adminNav.map((item) => {
            const isActive = pathname === item.url || pathname.startsWith(item.url + '/');
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton 
                  isActive={isActive} 
                  render={<Link href={item.url} />}
                  className={isActive ? "bg-blue-50 text-blue-600 hover:bg-blue-100" : "text-zinc-900"}
                  tooltip={item.title}
                >
                  <item.icon className="size-4" />
                  <span className="font-medium">{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter className="px-4 pb-4 pt-0 group-data-[collapsible=icon]:p-2">
        <SidebarMenu>
          <SidebarMenuItem className="flex items-center flex-row">
            <SidebarMenuButton size="lg" className="h-12 hover:bg-transparent hover:text-inherit active:bg-transparent cursor-default p-0 flex-1 overflow-hidden">
              <Avatar className="size-10 rounded-md after:rounded-md">
                <AvatarFallback className="rounded-md">LS</AvatarFallback>
              </Avatar>
              <div className="flex flex-col gap-1 leading-none ml-2 group-data-[collapsible=icon]:hidden">
                <span className="font-semibold text-zinc-900 text-sm truncate">Luna Smith</span>
                <span className="text-xs text-zinc-500 truncate">Admin</span>
              </div>
            </SidebarMenuButton>
            <Button 
              variant="ghost" 
              size="icon" 
              className="text-zinc-500 hover:text-red-600 hover:bg-red-50 shrink-0 h-10 w-10 ml-1 group-data-[collapsible=icon]:hidden"
              onClick={() => logout()}
              disabled={isLoggingOut}
            >
              <RiLogoutBoxRLine className="size-4" />
            </Button>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      
      <SidebarRail />
    </Sidebar>
  )
}
