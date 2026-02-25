# Gemini 3 Agentic SWE Pipeline (KAIJU-VOICE Architecture) 🦖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Model: Gemini 3](https://img.shields.io/badge/Model-Gemini%203%20Pro%2FFlash-blue)](https://deepmind.google/technologies/gemini/)

A production-ready, autonomous AI agent pipeline built with **Gemini 3 Pro/Flash**.

This is the exact architecture we used to win **2nd Place at the Gemini 3 Tokyo Hackathon (hosted by Cerebral Valley)**. We built a complex, real-time multi-modal game ("KAIJU VOICE") in just 3 days using this pure "AI-Driven Development" approach.

Instead of typing "make this" into a chat UI, this project demonstrates how to orchestrate Gemini to autonomously handle **Requirements → Architecture → Implementation → TDD → Quality Gates**.

## 🌟 Why We Built This

When building complex applications (Next.js App Router, TypeScript strict mode, multiple AI backend integrations), simple chat-based AI coding fails because:
1. **Context Amnesia**: The AI forgets project constraints and previous files.
2. **Architecture Drift**: The codebase becomes an inconsistent mess of different patterns.
3. **The Infinite Bug Loop**: Fixing one bug creates two more.

Our solution: **Pipeline-as-Code** combined with Gemini 3's massive 1M+ token context window.

## 🚀 Key Features

*   **YAML-Driven Autonomous Workflows**: Development processes (like `new-feature`, `bug-fix`) are defined in YAML (`.agents/pipelines/`). Gemini executes them step-by-step.
*   **Specialized Agent Skills**: 50+ specialized prompts/skills (`.agents/skills/`) like `feature-architect`, `domain-modeler`, and `ui-approval-gate` to divide and conquer complex tasks.
*   **Intelligent Model Routing**: Uses **Gemini 3 Pro** for deep reasoning (Architecture/Design) and **Gemini 3 Flash** for blazing-fast code generation and self-healing loops.
*   **SSOT & 1M+ Token Context**: Uses `docs/features/` and `CONTEXT.json` as the Single Source of Truth. Gemini ingests the *entire* context and codebase every time, eliminating context amnesia.
*   **Dual Quality Gates**:
    *   **Readiness Gate (Pre-implementation)**: Validates specs against platform constraints (`constraints.json`).
    *   **Quality Gate (Post-implementation)**: Automatically runs ESLint, Vitest, and architecture checks (`make q.check`). If it fails, Gemini Flash self-heals in seconds.

## 🛠 Real-World Example: How We Built "KAIJU VOICE"

Here is how our AI agent actually built the core battle feature during the hackathon, moving from a simple prompt to a fully working UI and logic.

### 1. The Human Prompt
We gave the agent a simple command:
> "We need a real-time battle UI where a player's voice input is analyzed by Gemini 3 Flash and converted into damage against a Kaiju (e.g., Glacius). It must have a health bar, a microphone button, and a live commentary overlay."

### 2. Autonomous Architect & Spec Generation (Agent Action)
The agent (`feature-architect` skill) **did not write code yet**. First, it generated a formal Specification Document (`docs/features/001-kaiju-voice/SPEC.md`) and a Screen Layout (`screens/SCR-001.md`).

**Generated Screen Layout (`SCR-001.md`):**
```markdown
# Screen Layout: Battle Arena (SCR-001)

## Layout Structure
- **Top Bar**:
  - `div.health-bar-container` (Player vs Kaiju HP)
  - `span.round-timer`
- **Center Canvas**:
  - `img.kaiju-sprite` (Generated via Imagen 3)
  - `div.vfx-layer` (Framer Motion impact animations)
- **Bottom Controls**:
  - `button.mic-toggle` (Pulsing animation when active)
  - `div.voice-waveform` (Real-time visualizer)
- **Overlay**:
  - `div.live-commentary` (Gemini TTS Output Transcript)
```

### 3. Readiness Gate & Implementation (Agent Action)
The Readiness Gate validated that this layout met our `constraints.json` (e.g., "Must use Tailwind CSS", "Must use React Server Components where applicable"). Once passed, the `feature-implementer` agent started writing the React components and hooks based *strictly* on `SCR-001.md`.

### 4. Self-Healing Quality Gate (Agent Action)
During implementation, the agent made a TypeScript type error when connecting the Voice API.
1. `make q.check` ran automatically.
2. `vitest` failed with: `Error: Type 'string' is not assignable to type 'VoiceAnalysisResult'`.
3. The error log was fed back to Gemini 3 Flash.
4. **Within 8 seconds**, the agent fixed the type definition, re-ran the tests, got a Green build, and finalized the feature.

**The Result**: A perfectly typed, consistent, and beautiful Next.js component (`src/features/battle/presentation/BattleArena.tsx`) that exactly matched the initial spec, without human intervention during the coding phase.

## 🏗 Directory Structure Overview

The real magic lives in the `.agents` and `.quality` directories, acting as the brain and immune system of your codebase.

```text
├── .agents/
│   ├── pipelines/       # YAML definitions for autonomous workflows (new-feature, bug-fix)
│   ├── skills/          # 50+ specialized prompts (architect, implementer, reviewer)
│   └── state/           # State tracking (CONTEXT.json)
├── .quality/
│   └── scripts/         # Automated validation scripts (Python/Shell) for Quality Gates
├── docs/
│   ├── architecture/    # Platform constraints, ADRs, System Designs
│   └── features/        # SSOT Markdown specs generated by the Agent
├── src/                 # The actual Next.js application code generated by the Agent
└── Makefile             # Defines `make q.check` for the post-implementation Quality Gate
```

## 🎨 Architecture Diagrams

*(Included inside `docs/architecture/diagrams/` for your own presentations!)*

- [Agent Pipeline Workflows](docs/architecture/diagrams/03-agent-pipeline.svg)
- [Intelligent Model Routing](docs/architecture/diagrams/04-model-routing.svg)
- [Self-Healing Quality Gate](docs/architecture/diagrams/06-self-healing.svg)

## 💡 How to Use This Pattern in Your Projects

This repository serves as a **reference architecture** for Agentic SWE.

1.  **Adopt the Mindset**: Stop asking AI to write code directly. Ask it to write a spec (`docs/features/`), review the spec, and *then* implement it.
2.  **Use Context Files**: Create a `CONTEXT.json` and a `constraints.json` in your project. Pass these to Gemini in every prompt.
3.  **Build Quality Gates**: Wrap your linters and test runners in a script. Feed the error output back into Gemini Flash for instant self-healing.

## 🙏 Acknowledgements

Created for the **Gemini 3 Tokyo Hackathon** hosted by [Cerebral Valley](https://cerebralvalley.ai/). 
Built by team [Your Team Name / Handles].

---
*If you find this architecture useful, please give it a ⭐ on GitHub!*
