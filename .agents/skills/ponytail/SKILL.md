---
name: ponytail
description: Use when designing pragmatic, minimalist software architecture, eliminating over-engineering, pruning bloat, and enforcing deterministic simple code.---

# Ponytail Pragmatic Architecture

1. **Write less code, solve more problems**: Avoid convoluted abstractions. Use straightforward functions, standard libraries, and clean interfaces.
2. **Deterministic business logic first**: Calculations, formulas, and data processing must be completely deterministic and tested before wrapping in presentation or AI layers.
3. **Respect separation of concerns**:
   - Math / Engine: Pure deterministic algorithms.
   - LLM: Synthesis, explanation, advice.
   - Frontend: Clean presentation, reliable state handling.
4. **No premature optimization or over-engineering**: Solve the immediate user need cleanly with room to scale.
