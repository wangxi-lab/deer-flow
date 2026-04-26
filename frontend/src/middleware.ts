import { NextResponse, type NextRequest } from "next/server";

import {
  PASSWORD_AUTH_COOKIE,
  verifyPasswordAuthSession,
} from "@/server/password-auth";

function isPasswordAuthEnabledForMiddleware(): boolean {
  const publicEnabled = process.env.NEXT_PUBLIC_DEERFLOW_AUTH_ENABLED?.trim().toLowerCase();
  const serverEnabled = process.env.DEERFLOW_AUTH_ENABLED?.trim().toLowerCase();
  if (publicEnabled === "false" || serverEnabled === "false") {
    return false;
  }
  return (
    publicEnabled === "true" ||
    serverEnabled === "true" ||
    Boolean(process.env.DEERFLOW_AUTH_PASSWORD)
  );
}

export async function middleware(request: NextRequest) {
  if (!isPasswordAuthEnabledForMiddleware()) {
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
