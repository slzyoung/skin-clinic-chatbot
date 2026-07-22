import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

interface JwtPayload {
  sub?: string;
  type?: "STAFF" | "DOCTOR";
  roles?: string[];
  exp?: number;
}

function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, "=");
    const jsonPayload = atob(padded);
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("access_token")?.value;
  const payload = token ? parseJwt(token) : null;
  const isExpired = payload?.exp ? payload.exp * 1000 < Date.now() : true;
  const isAuthenticated = payload && !isExpired;

  // Determine home landing page based on role
  let homePath = "/login";
  if (isAuthenticated && payload) {
    if (payload.type === "DOCTOR") {
      homePath = "/doctor";
    } else if (payload.type === "STAFF") {
      const roles = payload.roles || [];
      if (roles.includes("ADMIN")) {
        homePath = "/admin/knowledge";
      } else {
        homePath = "/functional/ingest";
      }
    }
  }

  // Handle /login page for authenticated users
  if (pathname === "/login") {
    if (isAuthenticated) {
      return NextResponse.redirect(new URL(homePath, request.url));
    }
    return NextResponse.next();
  }

  // Handle /admin routes
  if (pathname.startsWith("/admin")) {
    if (!isAuthenticated) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
    if (payload?.type !== "STAFF") {
      return NextResponse.redirect(new URL("/doctor", request.url));
    }
    // If token includes roles array, enforce ADMIN role
    const roles = payload?.roles;
    if (roles && Array.isArray(roles) && roles.length > 0 && !roles.includes("ADMIN")) {
      return NextResponse.redirect(new URL("/functional/ingest", request.url));
    }
    return NextResponse.next();
  }

  // Handle /functional routes
  if (pathname.startsWith("/functional")) {
    if (!isAuthenticated) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
    if (payload?.type !== "STAFF") {
      return NextResponse.redirect(new URL("/doctor", request.url));
    }
    return NextResponse.next();
  }

  // Handle /doctor routes
  if (pathname.startsWith("/doctor")) {
    if (!isAuthenticated) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
    if (payload?.type !== "DOCTOR") {
      return NextResponse.redirect(new URL(homePath, request.url));
    }
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/functional/:path*", "/doctor/:path*", "/login"],
};
