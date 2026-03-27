"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Header } from "@/components/header";

export function ConditionalHeader() {
  const pathname = usePathname();
  const { user } = useAuth();

  // Auth pages have their own layout
  if (pathname.startsWith("/auth")) return null;
  // Homepage and About: only show the app Header when logged in (these pages have their own Navbar)
  if ((pathname === "/" || pathname === "/about") && !user) return null;

  return <Header />;
}
