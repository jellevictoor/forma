- small commits, short consice commit messages
- keep docker-compose runnable at all time
- use the ux/ui skill to pay attention to the Ux, really think with me for goo ideas

## Core Principles (Quick Reference)

- **Hexagonal Architecture**: Domain → Ports → Adapters (dependencies point inward)
- **TDD**: Write failing test → minimal code → refactor
- **Dependency Inversion**: Domain never depends on Adapters
- Use Pydantic `BaseModel` for domain models, not dicts
- prefer small clean methods that are understandable, follow SOLID principles
- prefer guard clauses. fail fast with return statements and avoid else in if statements

## Testing Strategy: Outside-In TDD (London School)

- IMPORTANT always use pytest
- **Workflow**: Always work from the outside in: Primary Adapter -> Application Use Case -> Domain Model -> Secondary Adapter.
- **TDD applies to ALL layers**: When adding new methods to ports/interfaces, you MUST write tests for the adapter implementation BEFORE writing the adapter code. Never implement adapter methods first and add tests after - that's not TDD.
- **1-Assert Rule**: Each test **MUST contain exactly one assert statement** to ensure atomic testing.
- **Verification**: Prioritize **State-Based Verification** (checking object state or return values). Avoid behavioral verification (method call spying) unless testing side-effects.
- **Inversion of Control**: Use Constructor Injection for all dependencies to facilitate test doubles.
- When running the test, run all the test unless instructed otherwise

## Project Architecture

This project follows **Hexagonal Architecture** (Ports & Adapters) with a clear separation between:

- **Application Layer**: Domain logic and use cases (analytics service, sync use cases)
- **Adapters**: Web (FastAPI routes + Jinja2 templates), Persistence (PostgreSQL)
- **Infrastructure**: External services (Strava API)

## Clean code guidelines

- always run `uv run ruff check` and fix the issues before being done with a task
- always run `uv run pytest tests/test_smoke.py` before committing — these catch DI wiring, missing attributes, and template errors that unit tests miss
- always use uv as dependency management and build tool

### General rules

    Follow standard conventions.
    Keep it simple stupid. Simpler is always better. Reduce complexity as much as possible.
    Boy scout rule. Leave the campground cleaner than you found it.
    Always find root cause. Always look for the root cause of a problem.

### Names rules

    Choose descriptive and unambiguous names.
    Make meaningful distinction.
    Use pronounceable and searchable names.
    Avoid acronyms and confusing names.
    Replace magic numbers with named constants.
    Avoid encodings. Don't append prefixes or type information.
    Choose names at the appropriate level of abstraction.

### Functions rules

    Small.
    Do one thing.
    Use descriptive names.
    Prefer fewer arguments (max 3).
    No arguments should be used as output.
    Don't use flag/boolean arguments. Split into independent methods.
    The method that changes state should return void or throw exception.
    The method that doesn't change state should return a value.
    Avoid duplication.

### Tests

    One assert per test.
    Readable.
    Follow TDD.
    Keep your test clean.
    Use the F.I.R.S.T rule: Fast, Independent, Repeatable, Self-validating, Timely.

### Design rules

    Keep configurable data at high levels.
    Prefer polymorphism to if/else or switch/case.
    Use dependency injection.
    Follow Law of Demeter. A class should know only its direct dependencies.

### Code smells

    Rigidity. The software is difficult to change.
    Fragility. The software breaks in many places due to a single change.
    Needless Complexity.
    Needless Repetition.
    Opacity. The code is hard to understand.

## Web Adapter Pattern

### API Endpoint Structure

Located in `/adapters/web/routes/`:

- Pattern: `/activities/{sport}/{page}`, `/analytics/{sport}`, `/progress`
- All URLs are path-param based — no query strings
- JSON data endpoints: `/api/overview/weekly-volume`, `/api/analytics/{sport}/volume`, etc.

Routes are thin — no business logic, only call the `AnalyticsService`.

## UI/UX Patterns

- Always use Tailwind CSS classes, minimise custom CSS
- **Never use inline `style="color:var(--color-*)"` or `style="background:var(--color-*)"` in templates** — use semantic Tailwind classes instead (`text-primary`, `text-muted`, `text-secondary`, `bg-surface`, `bg-surface-alt`, `border-edge`)
- The same rule applies to JS-generated HTML strings (e.g. inside `innerHTML = \`...\``)
- Always give feedback on submitted actions (loading state, success, error)
- Use Tailwind info/warning/error utility classes for feedback

### Page header pattern (every page)
Every page starts with this header block:
```html
<div class="mb-6">
  <h1 class="text-3xl font-bold text-primary">Page title</h1>
  <p class="text-xs text-muted mt-1">Short subtitle describing the page</p>
</div>
```

### Activity / sport accent pattern
When showing an activity with a sport type, use a left accent bar:
```html
<div class="flex items-center gap-3">
  <div class="w-1 h-10 rounded-full shrink-0" style="background:{{ sport_color }}"></div>
  <div>
    <p class="text-xs font-medium uppercase tracking-widest text-muted mb-0.5">meta info</p>
    <h1 class="text-3xl font-bold text-primary">{{ workout.name }}</h1>
  </div>
</div>
```
Note: `style="background:{{ sport_color }}"` is the one acceptable inline style since it comes from a Jinja2 variable; in JS-generated HTML use `style="background:${sportColor}"` similarly.

### Card section header pattern
```html
<h2 class="text-xs font-medium uppercase tracking-widest text-muted mb-5">Section title</h2>
```

### Form inputs pattern
All inputs/selects use these classes:
```
w-full px-3 py-2 border border-edge rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint/40 bg-surface text-primary
```

### Warning / stale state badge
```html
<div class="px-4 py-3 bg-amber/10 border border-amber/30 rounded-lg text-sm text-amber flex items-center gap-2">
```

### URL State Management

All URLs must be externally linkable. Parameters go in the path: `/{param}`, never `?=` query strings.

## Typography & UX Rules

### Capitalization
- Section headers use sentence case (e.g. "Weekly volume", "Personal records")
- Legend items use sentence case (e.g. "Running baseline", "Strength sessions")
- Prepositions are lowercase
- "forma" is the app name — the lowercase "f" is intentional, never capitalise it

### Numbers
- Use thousand separators with non-breaking spaces (`\u00a0`) for all numbers in tables (e.g. "22 914" not "22914")
- Use `font-variant-numeric: tabular-nums` on tables so digits align vertically. This is set globally in `static/css/theme.css` on `table`.
- Negative or loss values must use the CSS class `value-negative` (resolves to `var(--color-negative)`)
- Empty or zero-value cells show a muted dash (`—`) using the CSS class `value-empty` (resolves to `var(--color-empty)`)

### Tables
- Use zebra striping on data tables — handled globally via `tbody tr:nth-child(even)` in `theme.css` using `var(--color-surface-alt)`
- Hide sport columns entirely when there is no data for that sport

### Theme & dark mode
- The app supports light / dark / system modes via a toggle in the nav
- Theme class `dark` is toggled on `<html>`; preference is stored in `localStorage`
- All colors are defined as CSS custom properties in `theme.css` (`:root` for light, `.dark` for dark)
- Tailwind is configured with `darkMode: 'class'` and semantic color extensions that reference CSS variables
- Use semantic Tailwind classes in templates: `bg-surface`, `bg-surface-alt`, `border-edge`
- Use CSS variables directly in D3 charts via `.style('fill', 'var(--color-mint)')` etc.
- The sidebar (`--color-nav`) is **light in light mode** (`#F5F4F1`) and dark in dark mode (`#1A1916`) — nav link text and hover states use `--color-nav-text` / `--color-nav-hover` CSS vars (not hardcoded white opacities)
- Nav icon buttons use the `.nav-btn` CSS class for theme-adaptive hover (not `hover:bg-white/10`)

### Charts
- SVG with `viewBox` fills container width (no fixed pixel widths)
- Use d3.js to generate all graphs
- Always use CSS variables for colors in D3 — never hardcoded hex values
- Brand colors — respect them in all charts and sport indicators:
    nav:          var(--color-nav)         light: #F5F4F1  dark: #1A1916
    accent:       var(--color-accent)      #0C9B6E  (brand/logo, teal-green)
    mint:         var(--color-mint)        #2DD4AA  (running)
    sky:          var(--color-sky)         #60A5FA  (strength)
    amber:        var(--color-amber)       #FB923C  (climbing)
    page bg:      var(--color-bg)          light: #EDECEA  dark: #111009
    surface:      var(--color-surface)     light: #FAFAF8  dark: #1A1916
    surface-alt:  var(--color-surface-alt) light: #F2F0EB  dark: #231F1B
    edge:         var(--color-edge)        light: #DCD9D1  dark: #312D28
- Sport color mapping:
    running   → mint   var(--color-mint)   #2DD4AA
    strength  → sky    var(--color-sky)    #60A5FA
    climbing  → amber  var(--color-amber)  #FB923C
- Use `.sport-run`, `.sport-strength`, `.sport-climbing` CSS classes for sport indicator dots
- When showing multiple timeseries, always align the x-axis vertically across charts on the page

### Tooltip Labels
- Write labels in full (e.g. "Average pace:", not "Avg pace:")
