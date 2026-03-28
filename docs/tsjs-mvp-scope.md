# TS/JS MVP Scope

> **Note:** This document describes the original MVP scope defined before v0.5. The current implementation (v0.5+) supports `.js` and `.jsx` files via the TypeScript parser. For the current language support status, see [language-support-matrix.md](language-support-matrix.md).

## In Scope
- Relative import graph for `.ts` and `.tsx`
- `tsconfig.json` path alias resolution
- Barrel export resolution for `index.ts`
- Package boundary detection from workspace configuration
- Rule: cross-package-import-ban
- Rule: ui-to-infra-import-ban
- Rule: layer-leak-detection
- Rule: circular-module-detection

## Out of Scope (at MVP time)
- `.js` and `.jsx` parsing *(now supported since v0.5)*
- Dynamic imports
- Bundler-specific resolution
- Type inference
- Framework-specific decorators