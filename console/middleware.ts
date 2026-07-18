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
    // middleware requires an absolute redirect URL (relative Location throws
    // ERR_INVALID_URL here). nextUrl derives from the Host header, which the
    // reverse proxy forwards correctly — unlike route handlers, middleware
    // never sees the container bind address.
    const login = request.nextUrl.clone();
    login.pathname = "/login";
    login.search = "";
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
