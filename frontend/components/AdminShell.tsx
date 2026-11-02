"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { adminLogout, hasToken } from "@/lib/api";

const NAV = [{ href: "/admin", label: "Documents" }, { href: "/admin/tickets", label: "Tickets" }, { href: "/admin/analytics", label: "Analytics" }];

export function useAuthGuard() {
  const router = useRouter();
  const [ok, setOk] = useState(false);
  useEffect(() => { if (hasToken()) setOk(true); else router.replace("/admin/login"); }, [router]);
  return { ok, expired: () => { adminLogout(); router.replace("/admin/login"); } };
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { ok } = useAuthGuard();
  if (!ok) return <p className="p-8 text-ink/60">Checking sign-in…</p>;
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-ink/15 pb-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="text-xl font-semibold">CampusVoice <span className="text-sm font-normal text-ink/60">admin</span></Link>
          <nav aria-label="Admin" className="flex gap-4 text-sm">
            {NAV.map((n) => <Link key={n.href} href={n.href} aria-current={path === n.href ? "page" : undefined} className={path === n.href ? "font-semibold underline underline-offset-4" : "text-ink/70 hover:underline"}>{n.label}</Link>)}
          </nav>
        </div>
        <button type="button" onClick={() => { adminLogout(); router.replace("/admin/login"); }} className="text-sm underline">Sign out</button>
      </header>
      {children}
    </div>
  );
}
