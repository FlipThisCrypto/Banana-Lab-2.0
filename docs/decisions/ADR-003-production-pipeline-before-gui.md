# ADR-003: The production pipeline comes before the GUI

**Status:** Accepted · **Date:** 2026-07-28

## Context

Banana Lab 1.0 grew a substantial application — a studio UI, a character bible
review app, workflow orchestration, agent stage definitions. It shipped an issue
whose page 2 contained no valid artwork.

The software was not the bottleneck. The production method was.

## Decision

Build the **workflow, the schemas and the quality gates** first. Build only the
software that serves them.

This run delivers a CLI (`status`, `validate`, `schemas`, `comfy`, `dashboard`)
and a static HTML dashboard. Both are views over the filesystem. Neither can
approve anything or advance a stage.

A richer GUI is deferred until the pipeline has produced one approved issue.

## Consequences

**Good**

- Effort goes into the thing that was actually broken.
- The workflow is validated by use before it is encoded in a UI.
- A GUI built later can be built against a proven contract.

**Costs**

- No visual asset browser yet. Reviewers open directories.
- Approval is hand-edited YAML, which is deliberate friction.

## Alternatives rejected

- **Port the 1.0 GUI.** It encodes the workflow that produced the failure.
- **Build the dashboard first.** A dashboard over an unproven pipeline shows
  green boxes for work that is not done — which is precisely what the legacy QA
  report did.
