"use client";

import { useAuth } from "@/lib/auth";
import { AuthGuard } from "@/components/auth-guard";
import SearchBar from "@/components/search-bar";
import { Navbar } from "@/components/home/Navbar";
import { Hero } from "@/components/home/Hero";
import { PlatformStrip } from "@/components/home/PlatformStrip";
import { ValueSection } from "@/components/home/ValueSection";
import { FeaturesSection } from "@/components/home/FeaturesSection";
import { RoadmapSection } from "@/components/home/RoadmapSection";
import { CtaSection } from "@/components/home/CtaSection";
import { Footer } from "@/components/home/Footer";

function AppHome() {
  return (
    <AuthGuard>
      <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4">
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground mb-3">
            Quant<span style={{ color: "var(--home-purple)" }}>Cortex</span>
          </h1>
          <p className="text-muted-foreground text-lg">
            AI-powered research for Indian equities — BSE data, FinBERT analysis, multi-agent forecasts
          </p>
        </div>
        <SearchBar />
        <p className="mt-6 text-muted-foreground text-sm">
          Type a company name or ticker to get started
        </p>
      </main>
    </AuthGuard>
  );
}

function LandingPage() {
  return (
    <div style={{ background: "var(--home-bg)", color: "var(--home-text)", fontFamily: "var(--font-sans)" }}>
      <Navbar />
      <Hero />
      <PlatformStrip />
      <ValueSection />
      <FeaturesSection />
      <RoadmapSection />
      <CtaSection />
      <Footer />
    </div>
  );
}

export default function Page() {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ minHeight: "100vh", background: "var(--home-bg)" }} />;
  if (user) return <AppHome />;
  return <LandingPage />;
}
