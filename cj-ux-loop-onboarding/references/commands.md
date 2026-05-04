# `uxl` Command Quick Reference

## Install

```bash
npm i -D @damsleth/ux-loop playwright
```

Optional for OpenAI review runner:

```bash
npm i openai
```

## Initialize

```bash
uxl init
uxl init --non-interactive
uxl init --force
```

## Flow Mapping

```bash
uxl flows list
uxl flows check
uxl flows add --id <id> --label <label> [--path <path>] [--to <flowName>]
uxl flows map --id <inventoryId> --to <flowName[,flowName]>
uxl flows import-playwright --yes
```

## Pipeline

```bash
uxl shots
uxl review
uxl implement
uxl run
```

## Overrides

```bash
uxl review --runner codex
uxl review --runner openai --model <model>

uxl implement --target current
uxl implement --target branch --branch <name>
uxl implement --target worktree --worktree <path>
```

## Useful npm scripts

```json
{
  "scripts": {
    "uxl:init": "uxl init",
    "uxl:flows": "uxl flows check",
    "uxl:shots": "uxl shots",
    "uxl:review": "uxl review",
    "uxl:implement": "uxl implement",
    "uxl:run": "uxl run"
  }
}
```
