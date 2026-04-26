export const PASSWORD_AUTH_COOKIE = "deerflow_auth";

const DEFAULT_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function isPasswordAuthEnabled(): boolean {
  const enabled = process.env.DEERFLOW_AUTH_ENABLED?.trim().toLowerCase();
  if (enabled === "false") {
    return false;
  }
  return enabled === "true" || Boolean(process.env.DEERFLOW_AUTH_PASSWORD);
}

export function getPasswordAuthUsername(): string {
  return process.env.DEERFLOW_AUTH_USERNAME ?? "admin";
}

export function isPasswordAuthConfigured(): boolean {
  return Boolean(process.env.DEERFLOW_AUTH_PASSWORD);
}

export function getPasswordAuthMaxAgeSeconds(): number {
  const raw = process.env.DEERFLOW_AUTH_SESSION_MAX_AGE_SECONDS;
  if (!raw) {
    return DEFAULT_SESSION_MAX_AGE_SECONDS;
  }
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value <= 0) {
    return DEFAULT_SESSION_MAX_AGE_SECONDS;
  }
  return value;
}

export function verifyPasswordCredentials({
  username,
  password,
}: {
  username: string;
  password: string;
}): boolean {
  const expectedPassword = process.env.DEERFLOW_AUTH_PASSWORD;
  if (!expectedPassword) {
    return false;
  }
  return (
    safeEqual(username, getPasswordAuthUsername()) &&
    safeEqual(password, expectedPassword)
  );
}

export async function createPasswordAuthSession(
  username: string,
): Promise<string> {
  const expiresAt = Math.floor(Date.now() / 1000) + getPasswordAuthMaxAgeSeconds();
  const payload = base64UrlEncode(
    JSON.stringify({
      sub: username,
      exp: expiresAt,
    }),
  );
  const signature = await sign(payload);
  return `${payload}.${signature}`;
}

export async function verifyPasswordAuthSession(
  value: string | undefined,
): Promise<{ username: string } | null> {
  if (!value) {
    return null;
  }
  const [payload, signature] = value.split(".");
  if (!payload || !signature) {
    return null;
  }
  const expectedSignature = await sign(payload);
  if (!safeEqual(signature, expectedSignature)) {
    return null;
  }
  try {
    const parsed = JSON.parse(base64UrlDecode(payload)) as {
      sub?: unknown;
      exp?: unknown;
    };
    if (typeof parsed.sub !== "string" || typeof parsed.exp !== "number") {
      return null;
    }
    if (parsed.exp <= Math.floor(Date.now() / 1000)) {
      return null;
    }
    return { username: parsed.sub };
  } catch {
    return null;
  }
}

function getSigningSecret(): string {
  return (
    process.env.DEERFLOW_AUTH_SECRET ??
    process.env.BETTER_AUTH_SECRET ??
    process.env.AUTH_SECRET ??
    process.env.DEERFLOW_AUTH_PASSWORD ??
    "deerflow-local-password-auth-secret"
  );
}

async function sign(value: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(getSigningSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(value),
  );
  return base64UrlEncode(signature);
}

function safeEqual(left: string, right: string): boolean {
  const leftBytes = new TextEncoder().encode(left);
  const rightBytes = new TextEncoder().encode(right);
  const maxLength = Math.max(leftBytes.length, rightBytes.length);
  let diff = leftBytes.length ^ rightBytes.length;
  for (let index = 0; index < maxLength; index += 1) {
    diff |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }
  return diff === 0;
}

function base64UrlEncode(value: string | ArrayBuffer): string {
  const bytes =
    typeof value === "string"
      ? new TextEncoder().encode(value)
      : new Uint8Array(value);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

function base64UrlDecode(value: string): string {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = base64.padEnd(
    base64.length + ((4 - (base64.length % 4)) % 4),
    "=",
  );
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
