import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  createPasswordAuthSession,
  getPasswordAuthMaxAgeSeconds,
  isPasswordAuthConfigured,
  isPasswordAuthEnabled,
  PASSWORD_AUTH_COOKIE,
  verifyPasswordCredentials,
} from "@/server/password-auth";
import { loadPasswordAuthEnv } from "@/server/password-auth-env";

export const runtime = "nodejs";

export async function POST(request: Request) {
  loadPasswordAuthEnv();

  if (!isPasswordAuthEnabled()) {
    return NextResponse.json({ ok: false, error: "AUTH_DISABLED" }, { status: 400 });
  }
  if (!isPasswordAuthConfigured()) {
    return NextResponse.json(
      {
        ok: false,
        error: "AUTH_NOT_CONFIGURED",
        message: "Set DEERFLOW_AUTH_PASSWORD before enabling password auth.",
      },
      { status: 500 },
    );
  }

  const body = (await request.json().catch(() => null)) as {
    username?: unknown;
    password?: unknown;
  } | null;
  const username = typeof body?.username === "string" ? body.username : "";
  const password = typeof body?.password === "string" ? body.password : "";

  if (!verifyPasswordCredentials({ username, password })) {
    return NextResponse.json(
      { ok: false, error: "INVALID_CREDENTIALS" },
      { status: 401 },
    );
  }

  const cookieStore = await cookies();
  cookieStore.set(PASSWORD_AUTH_COOKIE, await createPasswordAuthSession(username), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: getPasswordAuthMaxAgeSeconds(),
  });

  return NextResponse.json({ ok: true });
}
