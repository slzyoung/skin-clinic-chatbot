import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { FunctionalSidebar } from "@/components/layout/FunctionalSidebar"
import { Input } from "@/components/ui/input"
import { RiSearchLine } from "@remixicon/react"
import { RouteGuard } from "@/components/auth/route-guard"

export default function FunctionalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <RouteGuard allowedTypes={["STAFF"]} requiredRole="FUNCTIONAL">
      <SidebarProvider>
        <FunctionalSidebar />
        <SidebarInset className="bg-background">
          <header className="sticky top-0 z-10 flex shrink-0 items-center border-b p-4 bg-background">
            <div className="flex w-full max-w-md items-center relative">
              <RiSearchLine className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground size-4" />
              <Input
                type="search"
                placeholder="Search for knowledge, product, or treatment"
                className="pl-9 bg-white"
              />
            </div>
          </header>
          <div className="flex-1 overflow-auto relative">
            {children}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </RouteGuard>
  )
}
