"use client";

import { Loader2Icon, LockKeyholeIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type LoginError = "AUTH_NOT_CONFIGURED" | "INVALID_CREDENTIALS" | "UNKNOWN";

const ERROR_MESSAGES: Record<LoginError, string> = {
  AUTH_NOT_CONFIGURED:
    "认证已启用，但还没有配置 DEERFLOW_AUTH_PASSWORD。请先在环境变量中设置密码并重启服务。",
  INVALID_CREDENTIALS: "账号或密码不正确。",
  UNKNOWN: "登录失败，请稍后重试。",
};

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/workspace";
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<LoginError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/password-auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      const payload = (await response.json().catch(() => null)) as {
        error?: string;
      } | null;

      if (!response.ok) {
        if (payload?.error === "AUTH_NOT_CONFIGURED") {
          setError("AUTH_NOT_CONFIGURED");
        } else if (payload?.error === "INVALID_CREDENTIALS") {
          setError("INVALID_CREDENTIALS");
        } else {
          setError("UNKNOWN");
        }
        return;
      }

      router.replace(callbackUrl);
      router.refresh();
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="rounded-[2rem] border border-stone-100/15 bg-stone-950/55 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl md:p-8">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-2xl bg-amber-200 text-stone-950">
          <LockKeyholeIcon className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">账号密码登录</h2>
          <p className="text-sm text-stone-400">使用配置的本地管理员账号进入</p>
        </div>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm text-stone-300" htmlFor="username">
            账号
          </label>
          <Input
            id="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="border-stone-100/15 bg-stone-900/70 text-stone-50 placeholder:text-stone-500"
            placeholder="admin"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm text-stone-300" htmlFor="password">
            密码
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="border-stone-100/15 bg-stone-900/70 text-stone-50 placeholder:text-stone-500"
            placeholder="输入密码"
          />
        </div>

        {error && (
          <div className="rounded-2xl border border-red-300/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {ERROR_MESSAGES[error]}
          </div>
        )}

        <Button
          type="submit"
          disabled={isSubmitting}
          className="h-12 w-full rounded-2xl bg-amber-200 text-base font-semibold text-stone-950 hover:bg-amber-100"
        >
          {isSubmitting && <Loader2Icon className="size-4 animate-spin" />}
          登录
        </Button>
      </form>
    </div>
  );
}
