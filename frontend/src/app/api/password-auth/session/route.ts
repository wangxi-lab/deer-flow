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

  const enabled = isPasswordAuthEnabled();
  const configured = isPasswordAuthConfigured();
  const cookieStore = await cookies();
  const session = await verifyPasswordAuthSession(
    cookieStore.get(PASSWORD_AUTH_COOKIE)?.value,
  );

  return NextResponse.json({
    enabled,
    configured,
    authenticated: Boolean(session),
    username: session?.username ?? null,
  });
}
