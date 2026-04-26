import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { PASSWORD_AUTH_COOKIE } from "@/server/password-auth";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(PASSWORD_AUTH_COOKIE);
  return NextResponse.json({ ok: true });
}
