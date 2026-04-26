import { NextResponse, type NextRequest } from "next/server";

import {
  isPasswordAuthEnabled,
  PASSWORD_AUTH_COOKIE,
  verifyPasswordAuthSession,
} from "@/server/password-auth";

export async function middleware(request: NextRequest) {
  if (!isPasswordAuthEnabled()) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;
  const session = await verifyPasswordAuthSession(
    request.cookies.get(PASSWORD_AUTH_COOKIE)?.value,
  );

  if (pathname === "/login") {
    if (session) {
      return NextResponse.redirect(new URL("/workspace", request.url));
    }
    return NextResponse.next();
  }

  if (pathname.startsWith("/workspace") && !session) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set(
      "callbackUrl",
      `${request.nextUrl.pathname}${request.nextUrl.search}`,
    );
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/login", "/workspace/:path*"],
};
