# AGENTS.md — Arya Noble Frontend Agent Configuration

> **Core Directive:** ALWAYS refer to `docs/DESIGN.md` before building UI components. `DESIGN.md` is the strict source of truth for design patterns, tokens, and CSS best practices.

Next.js 16 + React 19 frontend utilizing Tailwind CSS v4 and Shadcn UI.

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages and layouts
│   │   ├── admin/           # Admin Dashboard (knowledge, users, categories, configuration, etc.)
│   │   ├── doctor/          # Doctor Portal (chat assistant, patient history)
│   │   ├── globals.css      # Global Tailwind directives and CSS variables
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/
│   │   ├── ui/              # shadcn/ui primitives - DO NOT edit directly unless modifying base styles
│   │   └── shared/          # Reusable composite components
│   ├── hooks/               # Custom React hooks (React Query / TanStack Query hooks)
│   └── lib/
│       ├── axios.ts         # Central Axios client instance (baseURL: http://localhost:8000/api)
│       └── utils.ts         # Utility functions
├── components.json          # shadcn/ui configuration
├── next.config.ts           # Next.js configuration
├── package.json             # Dependencies
└── tailwind.config.ts       # Tailwind configuration
```

## Backend & RAG Integration Workflow

The frontend connects to the unified FastAPI Backend service running on `http://localhost:8000/api`:

| Feature Area | Frontend Route / Component | Backend Endpoint | Integration Details |
|---|---|---|---|
| **Doctor AI Chat** | `/doctor/chat` | `POST /api/chats/` & `POST /api/chats/{id}/messages` | Sends user messages; backend RAG engine generates AI answers with citations `[1]`, `[2]` via background tasks. |
| **Knowledge Base Upload** | `/admin/knowledge` | `POST /api/ai/ingest` & `GET /api/knowledge/` | Uploads files via `POST /api/ai/ingest` (Docling + CustomChunker + PGVector/BM25) and tracks status via `GET /api/knowledge/`. |
| **Interactive AI Refinement** | `/admin/knowledge` | `POST /api/ai/ingest/pending/{file}/refine` | Allows admins to refine chunk content via natural language prompt instructions. |
| **Configuration** | `/admin/configuration` | `GET/PUT /api/config/` | Updates active LLM keys, models (`gpt-4o-mini`), and system settings. |

## Agent Instructions & Rules

- **Component Creation:** Place reusable components in `src/components/shared/`. If it's a Shadcn component, the CLI will place it in `src/components/ui/`.
- **Use the Shadcn Skill:** When adding new Shadcn UI components, you **MUST** use the Shadcn CLI: `npx shadcn add <component_name>`.
- **Task Tracking (`TODO.md`):** After completing a slicing task and receiving confirmation from the user, you **MUST** update `TODO.md` by marking the relevant checkbox as `[x]`.
- **Pages:** Follow the Next.js App Router conventions inside `src/app/`.
- **State/Hooks:** Custom hooks go in `src/hooks/`, utility functions go in `src/lib/`.
- **Aliases:** Use `@/*` to import from the `src/` directory (e.g., `@/components/ui/button`, `@/lib/utils`).

## Tech Stack Context

| Library | Purpose |
|---------|---------|
| Next.js 16 | Framework (App Router) |
| React 19 | UI Library |
| Tailwind CSS v4 | Utility-first styling |
| shadcn/ui | Headless component primitives (base-mira style) |
| remixicon | Icon library |
| TanStack Query | Server state management & API data fetching |

## Commands

| Action | Command |
|--------|---------|
| Dev server | `pnpm dev` (or `npm run dev`) |
| Add Shadcn Component | `npx shadcn add <component>` |
| Build | `pnpm build` |
| Lint | `pnpm lint` |