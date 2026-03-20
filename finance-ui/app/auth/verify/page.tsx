"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

function VerifyContent() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token found.");
      return;
    }
    fetch(`${API}/auth/verify?token=${encodeURIComponent(token)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "verified") {
          setStatus("success");
          const alreadyLoggedIn = !!localStorage.getItem("auth_token");
          // Notify any other open app tabs to refresh user data
          try { new BroadcastChannel("auth").postMessage("verified"); } catch {}
          setMessage("Email verified! Taking you back to the app...");
          setTimeout(() => router.replace(alreadyLoggedIn ? "/" : "/auth/login"), 2000);
        } else {
          setStatus("error");
          setMessage(data.detail ?? "Verification failed.");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("Something went wrong. Please try again.");
      });
  }, [token, router]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Finance<span className="text-primary">RAG</span>
        </h1>

        <div className="mt-8 rounded-xl border border-border bg-card p-8">
          {status === "loading" && (
            <>
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <p className="text-muted-foreground">Verifying your email...</p>
            </>
          )}
          {status === "success" && (
            <>
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
                <span className="text-2xl">✓</span>
              </div>
              <h2 className="text-lg font-semibold text-green-400 mb-2">Email Verified</h2>
              <p className="text-sm text-muted-foreground">{message}</p>
            </>
          )}
          {status === "error" && (
            <>
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
                <span className="text-2xl">✕</span>
              </div>
              <h2 className="text-lg font-semibold text-red-400 mb-2">Verification Failed</h2>
              <p className="text-sm text-muted-foreground mb-4">{message}</p>
              <button
                onClick={() => router.replace("/auth/login")}
                className="text-sm text-primary hover:underline"
              >
                Back to login
              </button>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <VerifyContent />
    </Suspense>
  );
}
