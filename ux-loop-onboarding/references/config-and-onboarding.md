# Config and Onboarding Notes

## Minimal config skeleton

```js
import { defineUxlConfig } from "@damsleth/ux-loop"

export default defineUxlConfig({
  capture: {
    runner: "playwright",
    baseUrl: process.env.UI_REVIEW_BASE_URL || "http://127.0.0.1:5173",
    timeoutMs: 120000,
    onboarding: { status: "pending" },
    flowInventory: [
      { id: "home", label: "Homepage", path: "/", required: true },
    ],
    flowMapping: {
      home: ["home"],
    },
    playwright: {
      startCommand: "dev",
      devices: [
        { name: "mobile", width: 390, height: 844 },
        { name: "desktop", width: 1280, height: 800 },
      ],
      flows: [
        {
          label: "Homepage",
          name: "home",
          path: "/",
          waitFor: "main",
          settleMs: 250,
          screenshot: { fullPage: true },
        },
      ],
    },
  },
  review: {
    runner: "codex",
  },
  implement: {
    target: "worktree",
  },
})
```

## Coverage rules

- `uxl shots` fails unless required-flow coverage is complete.
- Coverage requires every `capture.flowInventory` entry with `required: true` to map to one or more valid `capture.playwright.flows[].name` values via `capture.flowMapping`.
- `capture.flowMapping` IDs must exist in `flowInventory`.
- `capture.flowInventory[].id` should be slug-case.
- Keep `capture.onboarding.status` as `pending` until coverage is complete.

## Runner notes

- `review.runner` supports `codex` and `openai`.
- OpenAI runner requires a model and API key (`OPENAI_API_KEY` by default).
- `implement.target` supports `current`, `branch`, and `worktree`.

## Optional custom capture adapter

Set:

- `capture.runner = "custom"`
- `capture.adapter = "./uxl.capture.mjs"`

Adapter must export:

```js
export async function captureUx(context) {
  return [{ label: "Flow label", files: ["/abs/or/relative/path.png"] }]
}
```
