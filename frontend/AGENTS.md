# AGENTS.md — Arya Noble Frontend Agent Configuration

> **Core Directive:** ALWAYS refer to `docs/DESIGN.md` before building UI components. `DESIGN.md` is the strict source of truth for design patterns, tokens, and CSS best practices.

Next.js 16 + React 19 frontend utilizing Tailwind CSS v4 and Shadcn UI.

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages and layouts
│   │   ├── globals.css      # Global Tailwind directives and CSS variables
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/
│   │   ├── ui/              # shadcn/ui primitives (Button, Input, etc.) - DO NOT edit directly unless modifying base styles
│   │   └── shared/          # Reusable composite components (e.g., Navigation, Cards)
│   ├── hooks/               # Custom React hooks
│   └── lib/
│       └── utils.ts         # Utility functions, including cn() for Tailwind classes
├── components.json          # shadcn/ui configuration (style: base-mira, iconLibrary: remixicon)
├── next.config.ts           # Next.js configuration
├── package.json             # Dependencies
└── tailwind.config.ts       # Tailwind configuration (if applicable, though v4 relies heavily on CSS vars)
```

## Agent Instructions & Rules

- **Component Creation:** Place reusable components in `src/components/shared/`. If it's a Shadcn component, the CLI will place it in `src/components/ui/`.
- **Use the Shadcn Skill:** When adding new Shadcn UI components, you **MUST** use the Shadcn CLI: `npx shadcn add <component_name>`.
- **Task Tracking (`TODO.md`):** After completing a slicing task and receiving confirmation from the user, you **MUST** update `TODO.md` by marking the relevant checkbox as `[x]`.
- **Pages:** Follow the Next.js App Router conventions inside `src/app/`.
- **State/Hooks:** Custom hooks go in `src/hooks/`, utility functions go in `src/lib/`.
- **Aliases:** Use `@/*` to import from the `src/` directory (e.g., `@/components/ui/button`, `@/lib/utils`).

## Slicing Workflow

When instructed to slice a design from Figma:
1. **Analyze:** Check `docs/DESIGN.md` for existing design tokens (colors, typography).
2. **Shadcn First:** If a component can be built using a Shadcn primitive, use it. 
3. **Icons:** We use `remixicon`. Import them as React components via `@remixicon/react`. **Never** use `lucide-react`, even if a boilerplate tool generates it.
4. **Accessibility (a11y):** Ensure all interactive elements are accessible. Add `aria-label`s and screen-reader only text (`sr-only`) for icon-only buttons.
5. **Verify Constraints:** BEFORE finalizing the component or asking for user review, you **MUST** double-check your code against `docs/DESIGN.md` to ensure no explicit design constraints (e.g., border radii, shadows, responsive layout rules) were accidentally overridden by generic templates.

## Tech Stack Context

| Library | Purpose |
|---------|---------|
| Next.js 16 | Framework (App Router) |
| React 19 | UI Library |
| Tailwind CSS v4 | Utility-first styling |
| shadcn/ui | Headless component primitives (base-mira style) |
| remixicon | Icon library |

## Commands

| Action | Command |
|--------|---------|
| Dev server | `npm run dev` |
| Add Shadcn Component | `npx shadcn add <component>` |
| Build | `npm run build` |
| Lint | `npm run lint` |

## Best Practices & Guidelines

- **Double-Check Design Rules:** Always perform a final manual review of your component code against `docs/DESIGN.md` before ending your turn. Boilerplate generators (like Shadcn CLI) often output code that violates project-specific constraints.

- **Server vs. Client Components:** Default to Server Components. Only add `"use client"` at the very top of a file when it absolutely requires interactivity (e.g., `useState`, `useEffect`, `onClick`, or browser APIs). Push `"use client"` as far down the component tree as possible.
- **File Naming Conventions:** Use `kebab-case` for all component and utility files (e.g., `doctor-details-sheet.tsx`, `date-formatter.ts`) for consistency.
- **Strict Type Safety:** Never use `any`. Always define strict `interface` or `type` aliases for component props and data models.
- **Colocation Principle:** Keep helper functions, sub-components, and types close to where they are used. If a type is only used in one specific route or feature, keep it in that local directory rather than polluting the global `src/lib/` or `src/components/shared/` folders.
- **Form Handling:** Always use `@tanstack/react-form` combined with `zod` for all form state management and validations.
- **Zod Schemas:** Always define Zod schemas in a separate `schema.ts` (or appropriately named) file alongside the component or feature, rather than keeping them inline within the UI component file.
- **Error Handling:** Use React Error Boundaries for global/page-level rendering errors, and gracefully handle local component errors (e.g., inline error states). See `docs/integration.md` for API error handling.