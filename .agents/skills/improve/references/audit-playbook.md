# Audit Playbook

Detailed guidelines and heuristics for surveying a codebase across the 9 core categories.

## Category 1: Correctness & Bugs
- **Boundary conditions**: Division by zero, empty arrays, null/undefined inputs, off-by-one indices.
- **Async/concurrency**: Unhandled promise rejections, race conditions in state updates, missing locks in file I/O.
- **Data conversions**: Implicit type coercion, timezone mismatches, invalid datetime parsing.
- **Error branches**: Silent catches (`try { ... } catch (e) {}`), swallowed errors, uninformative error messages.

## Category 2: Security
- **Authentication & Authorization**: Route protection, role enforcement, privilege escalation risks.
- **Injection & Sanitization**: SQL injection, XSS vectors, unescaped user inputs in DOM or templates.
- **Secrets & Credentials**: Hardcoded API keys, exposed service passwords, committed tokens.
- **CORS & Headers**: Overly permissive CORS settings, missing security headers (CSP, HSTS).

## Category 3: Performance
- **Database & Query efficiency**: N+1 queries, unindexed lookups, unbounded query limits.
- **Memory & Resource management**: Unclosed database connections, memory leaks in event listeners, large object cloning.
- **Frontend / Rendering**: Unnecessary DOM mutations, unmemoized expensive calculations, unoptimized images.
- **Network & Caching**: Cache header optimization, redundant API roundtrips, missing stale-while-revalidate.

## Category 4: Test Coverage
- **Core path coverage**: Uncovered critical business logic, physiological sports math calculations, financial flows.
- **Assertion quality**: Tests without assertions, asserting `is not None` without checking payload values.
- **Edge cases & Regressions**: Error paths and negative test cases.

## Category 5: Tech Debt & Architecture
- **Duplication**: Repeated business logic across routes or frontend handlers.
- **Coupling & Modularity**: Monolithic single files with too many responsibilities, circular imports.
- **Anti-patterns**: Bypassing domain models, inconsistent state management.

## Category 6: Dependencies & Migrations
- **Outdated libraries**: Packages with known vulnerabilities or deprecations.
- **Deprecated APIs**: Using deprecated SDK methods.
- **Lockfile consistency**: Synchronized dependencies between package manifests and lockfiles.

## Category 7: DX & Tooling
- **Build & script reliability**: Clean build scripts, fast rebuild times, reliable asset copying.
- **Linting & formatting**: Enforced code style, automated pre-commit checks.
- **Test runner ergonomics**: Fast isolated unit tests, clear failure logs.

## Category 8: Documentation
- **Configuration clarity**: Environment variable documentation (`.env.example`).
- **API specifications**: Accurate router docstrings, request/response models.
- **Runbooks & Guides**: Clear verification and deployment instructions.

## Category 9: Direction & Roadmap
- **Grounded enhancements**: Extending partially built modules, implementing open feature requests, addressing real user friction.
