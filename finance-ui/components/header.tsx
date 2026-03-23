"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function Header() {
  const { user, credits, logout } = useAuth();
  const router = useRouter();

  const handleResendVerification = async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080"}/auth/resend-verification`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    alert("Verification email resent. Check your inbox.");
  };

  if (!user) return null;

  const handleLogout = () => {
    logout();
    router.replace("/auth/login");
  };

  const isAdmin = user.role === "admin";
  const remaining = credits?.remaining ?? 0;
  const limit = credits?.limit ?? 10;
  const pct = isAdmin ? 100 : Math.round((remaining / limit) * 100);
  const creditColor =
    isAdmin ? "text-primary" : remaining <= 2 ? "text-red-400" : remaining <= 5 ? "text-yellow-400" : "text-green-400";

  return (
    <>
    {!user.is_verified && user.role !== "admin" && (
      <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-4 py-2 text-center text-xs text-yellow-400">
        Please verify your email to unlock full access.{" "}
        <button onClick={handleResendVerification} className="underline hover:text-yellow-300">Resend email</button>
      </div>
    )}
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" className="text-lg font-bold tracking-tight">
          Quant<span className="text-primary">Cortex</span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-4">
          {/* Credits */}
          <div className="flex items-center gap-2 text-sm">
            {isAdmin ? (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                Admin
              </span>
            ) : (
              <>
                {/* Credit bar */}
                <div className="hidden sm:flex items-center gap-2">
                  <div className="h-1.5 w-20 rounded-full bg-border overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className={`text-xs font-medium tabular-nums ${creditColor}`}>
                    {remaining}/{limit}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground hidden sm:block">credits</span>
              </>
            )}
          </div>

          {/* User email */}
          <span className="hidden md:block text-xs text-muted-foreground truncate max-w-[140px]">
            {user.email}
          </span>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
    </>
  );
}
