import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  isPasswordAuthConfigured,
  isPasswordAuthEnabled,
  PASSWORD_AUTH_COOKIE,
  verifyPasswordAuthSession,
} from "@/server/password-auth";
import { loadPasswordAuthEnv } from "@/server/password-auth-env";

export const runtime = "nodejs";

export async function GET() {
  loadPasswordAuthEnv();

  if (!isPasswordAuthEnabled()) {
    return new NextResponse(null, { status: 204 });
  }

  if (!isPasswordAuthConfigured()) {
    return NextResponse.json(
      {
        ok: false,
        error: "AUTH_NOT_CONFIGURED",
      },
      { status: 401 },
    );
  }

  const cookieStore = await cookies();
  const session = await verifyPasswordAuthSession(
    cookieStore.get(PASSWORD_AUTH_COOKIE)?.value,
  );

  if (!session) {
    return NextResponse.json(
      {
        ok: false,
        error: "UNAUTHORIZED",
      },
      { status: 401 },
    );
  }

  return new NextResponse(null, { status: 204 });
}
