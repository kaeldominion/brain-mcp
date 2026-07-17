import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/api/session") ||
    pathname.startsWith("/api/healthz") ||
    pathname.startsWith("/_next")
  ) {
    return NextResponse.next();
  }
  if (!request.cookies.get("bt")?.value) {
    // relative redirect: absolute URLs built from the request can carry the
    // container bind address (0.0.0.0) when behind a reverse proxy
    return new NextResponse(null, { status: 307, headers: { Location: "/login" } });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
