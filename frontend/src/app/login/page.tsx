import { Suspense } from "react";

import { LoginForm } from "./login-form";

export default function LoginPage() {
  return (
    <main className="relative flex min-h-screen overflow-hidden bg-[#11130f] text-stone-50">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(215,175,96,0.24),transparent_32%),radial-gradient(circle_at_80%_8%,rgba(108,145,119,0.26),transparent_28%),linear-gradient(135deg,#11130f_0%,#202315_45%,#0e1514_100%)]" />
      <div className="absolute top-[-18rem] right-[-10rem] size-[34rem] rounded-full border border-amber-200/10 bg-amber-200/5 blur-2xl" />
      <div className="absolute bottom-[-14rem] left-[-8rem] size-[30rem] rounded-full border border-emerald-200/10 bg-emerald-200/5 blur-2xl" />

      <section className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-6 py-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="max-w-2xl">
          <div className="mb-6 inline-flex rounded-full border border-stone-200/15 bg-stone-50/8 px-3 py-1 text-sm text-stone-200 backdrop-blur">
            DeerFlow Private Workspace
          </div>
          <h1 className="text-5xl leading-tight font-semibold tracking-[-0.04em] text-balance md:text-7xl">
            进入你的
            <span className="block text-amber-200">私有 Agent 工作台</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-stone-300">
            启用账号密码后，Workspace 会先验证登录态。适合把 DeerFlow
            部署在内网、云主机或需要简单访问控制的个人环境里。
          </p>
        </div>

        <Suspense>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
