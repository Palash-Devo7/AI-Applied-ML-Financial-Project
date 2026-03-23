# QuantCortex — Next.js Frontend

Production frontend for [quantcortex.in](https://quantcortex.in).

**Stack:** Next.js 15 (App Router) · TypeScript · Tailwind v4 · Lucide React · @vercel/analytics

## Local dev

```bash
npm install
npm run dev        # http://localhost:3000
```

Requires backend running at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key pages

| Route | Description |
|-------|-------------|
| `/` | Homepage (public) |
| `/auth/login` | Login |
| `/auth/register` | Register |
| `/auth/verify` | Email verification callback |
| `/company/[ticker]` | Company research page (chat + forecast + overview) |
| `/admin` | Admin dashboard (admin role only) |

## Key files

```
app/
  layout.tsx          — root layout, AuthProvider, Analytics
  page.tsx            — homepage (renders home/* components)
  admin/page.tsx      — admin dashboard (stats, users table)
  company/[ticker]/   — company research pages
  auth/               — login, register, verify pages

components/
  home/               — homepage sections (Navbar, Hero, DotCanvas, ...)
  header.tsx          — sticky app header (credits, admin button, logout)
  auth-guard.tsx      — redirects to /auth/login if no valid token

lib/
  api.ts              — all API calls, token management
  auth.tsx            — AuthProvider, useAuth hook
```

## Auth pattern

JWT stored in `localStorage`. All API calls go through `lib/api.ts` which injects the Bearer header automatically. `AuthProvider` restores token on mount and validates with `/auth/me`.

Admin-only pages check `user.role === "admin"` after auth loads — gated on `authLoading === false` to avoid race conditions.

## Rate limits (what the frontend handles)

The backend enforces three layers. The frontend handles the HTTP 429 responses:

| Layer | What triggers 429 | Response detail |
|---|---|---|
| slowapi (per-IP) | >5 req/min on query endpoints | Generic slowapi message |
| Credit system (per-user/day) | Daily credits exhausted | `{ error: "daily_credit_limit_reached", used, limit }` |
| Groq quota | Groq 30 RPM shared limit hit | `"QuantCortex is experiencing high demand..."` |

Credit usage is displayed in the header (remaining/limit bar). The credit count is refreshed after each credit-bearing request via `useAuth().refreshCredits()`.

## Deployment

Deployed on Vercel. Push to `main` triggers automatic deploy. No manual steps needed.

Environment variable set in Vercel dashboard:
```
NEXT_PUBLIC_API_URL=https://api.quantcortex.in
```
