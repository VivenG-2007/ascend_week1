"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, adminLogin } from "@/lib/api";

export default function AdminLogin() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true); setError(null);
    try { await adminLogin(String(f.get("username")), String(f.get("password"))); router.replace("/admin"); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Sign-in failed."); }
    finally { setBusy(false); }
  }
  return (
    <main className="mx-auto mt-24 max-w-sm rounded-lg border border-ink/10 bg-white p-6 shadow-sm">
      <h1 className="mb-4 text-2xl font-semibold">Staff sign-in</h1>
      <form onSubmit={submit} className="space-y-3">
        <label className="block">Username<input name="username" required autoComplete="username" className="mt-1 w-full rounded-md border border-ink/25 px-3 py-2" /></label>
        <label className="block">Password<input name="password" type="password" required autoComplete="current-password" className="mt-1 w-full rounded-md border border-ink/25 px-3 py-2" /></label>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-md bg-ink py-2 font-semibold text-white disabled:opacity-50">{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
