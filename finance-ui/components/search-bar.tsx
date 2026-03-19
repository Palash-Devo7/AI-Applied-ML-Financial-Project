"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { searchCompanies, loadCompany, type CompanyResult } from "@/lib/api";

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CompanyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [navigating, setNavigating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    searchCompanies(debouncedQuery)
      .then((data) => {
        setResults(data);
        setOpen(data.length > 0);
      })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [debouncedQuery]);

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectCompany = useCallback(
    (company: CompanyResult) => {
      setOpen(false);
      setQuery(company.name);
      setNavigating(true);
      // Fire-and-forget — don't block navigation on load
      loadCompany(company.ticker).catch(() => {});
      router.push(`/company/${company.ticker}`);
    },
    [router]
  );

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground h-5 w-5" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search companies — TCS, Reliance, Infosys…"
          className="w-full h-14 pl-12 pr-12 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground text-base focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
        />
        {(loading || navigating) && (
          <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground animate-spin" />
        )}
      </div>

      {open && (
        <ul className="absolute z-50 top-full mt-2 w-full bg-card border border-border rounded-xl overflow-hidden shadow-2xl">
          {results.map((r) => (
            <li key={r.ticker}>
              <button
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-muted transition-colors text-left"
                onMouseDown={() => selectCompany(r)}
              >
                <div>
                  <span className="text-foreground font-medium">{r.name}</span>
                  {r.group && (
                    <span className="ml-2 text-muted-foreground text-sm">Group {r.group}</span>
                  )}
                </div>
                <span className="text-muted-foreground text-sm font-mono">{r.ticker}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
