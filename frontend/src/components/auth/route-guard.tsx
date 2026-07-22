"use client";

import { useSession } from "@/hooks/use-session";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

interface RouteGuardProps {
  children: React.ReactNode;
  allowedTypes?: Array<"STAFF" | "DOCTOR">;
  requiredRole?: "ADMIN" | "FUNCTIONAL";
}

export function RouteGuard({
  children,
  allowedTypes,
  requiredRole,
}: RouteGuardProps) {
  const { user, isLoading, isError } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;

    if (isError || !user) {
      router.replace(`/login?from=${encodeURIComponent(pathname)}`);
      return;
    }

    if (allowedTypes && !(allowedTypes as string[]).includes(user.type)) {
      if (user.type === "DOCTOR") {
        router.replace("/doctor");
      } else {
        const isAdmin = user.roles.some((r) => r.name === "ADMIN");
        router.replace(isAdmin ? "/admin/knowledge" : "/functional/ingest");
      }
      return;
    }

    if (requiredRole && user.type === "STAFF") {
      const userRoles = user.roles.map((r) => r.name);
      if (requiredRole === "ADMIN" && !userRoles.includes("ADMIN")) {
        router.replace("/functional/ingest");
      } else if (
        requiredRole === "FUNCTIONAL" &&
        !userRoles.includes("ADMIN") &&
        !userRoles.includes("FUNCTIONAL")
      ) {
        router.replace("/login");
      }
    }
  }, [user, isLoading, isError, router, pathname, allowedTypes, requiredRole]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-sm text-muted-foreground">Authenticating session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
