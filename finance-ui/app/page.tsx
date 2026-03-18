import SearchBar from "@/components/search-bar";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      {/* Logo + tagline */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground mb-3">
          Finance<span className="text-primary">RAG</span>
        </h1>
        <p className="text-muted-foreground text-lg">
          AI-powered research for Indian equities — BSE data, FinBERT analysis, multi-agent forecasts
        </p>
      </div>

      {/* Search */}
      <SearchBar />

      {/* Hint */}
      <p className="mt-6 text-muted-foreground text-sm">
        Type a company name or ticker to get started
      </p>
    </main>
  );
}
