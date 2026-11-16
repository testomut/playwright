# Pixi.js E2E Automation — Playwright

A small, strongly typed Playwright test-automation project for the Pixi.js/Canvas demo game in
[testomut/pixijs-e2e-testing-demo](https://github.com/testomut/pixijs-e2e-testing-demo). This
repository contains **only** the Playwright automation — no application source, no Cypress. Tests
read as business scenarios; every Canvas/Pixi mechanic and every assertion is hidden behind a
small, deliberately narrow API.

**Application repository:** https://github.com/testomut/pixijs-e2e-testing-demo
**Live demo:** https://pixijs-e2e-testing-demo.vercel.app (see [Limitations](#limitations) — CI
does not test the deployed build)

This project is part of a Pixi.js E2E testing series:

1. [Why Canvas and Pixi.js Applications Are Hard to Test in E2E](https://medium.com/@testdream66/why-canvas-and-pixi-js-applications-are-hard-to-test-in-e2e-b95474640633)
2. [How Pixi.js Works Inside Canvas and Why It Matters for QA Automation](https://medium.com/@testdream66/how-pixi-js-works-inside-canvas-and-why-it-matters-for-qa-automation-a85c6ed59dac)

---

## Demo

<video src="docs/assets/pixi-e2e-demo.webm" controls width="480">
  Your browser doesn't support inline video - <a href="docs/assets/pixi-e2e-demo.webm">download the recording</a> instead.
</video>

A real Playwright pointer click on the Spin button — a Pixi.js Canvas object, not a DOM element —
triggering the spin animation, the reel content changing, the animation completing, and the final
win result becoming visible. This is a genuine recording of the "player completes a winning spin"
scenario (`e2e/game.spec.ts`), not a screen capture — see [Video recording](#video-recording) for
how it was produced.

## Why normal DOM locators can't target Pixi objects

The game is a small slot-style demo rendered entirely inside a single `<canvas>` element. Once the
player starts the game, everything — the Spin button, balance, reels, result text — is drawn
pixels on that canvas. `page.getByRole(...)`, `page.getByText(...)`, and CSS selectors all return
nothing for it, because there's no DOM node to find. The only way to interact with it reliably is
through structured information the application chooses to expose (`window.__TEST_APP__`), and a
real pointer click at the right screen coordinates.

## Architecture

```
spec (e2e/game.spec.ts)
  ↓
fixture (game.fixture.ts)
  ↓
GamePage — business/user flow, assertions, and the page's declared DOM/Pixi element surface
  ↓                                      ↓
PixiController                     ApiRequests
Canvas/Pixi mechanics: bounds,     Network mechanics: response
text, coordinate conversion,       observation, mocking, JSON
phase polling                      parsing
  ↓                                      ↓
window.__TEST_APP__ (read-only)     /api/game/spin
  ↓
Pixi.js application
```

```
e2e/game.spec.ts        every scenario - business-level method calls only
fixtures/game.fixture.ts player, game, startedGame
pages/GamePage.ts        declared DOM selectors + typed Pixi elements, user-facing flow, all assertions (verify*)
support/PixiController.ts  the only Pixi/Canvas-specific code in this project
support/ApiRequests.ts   the only network-specific code in this project
types/game.types.ts      GamePhase, GameResult, SpinMockResult, Player, ReelSymbols, SpinApiResponse, SpinHttpResult, GameSnapshot
types/pixi.types.ts      ButtonLabel/TextLabel/DisplayLabel, PixiObjectBounds, TestBridge
playwright.config.ts
```

No separate `assertions/`, `drivers/`, `data/`, or `utils/` layers - those responsibilities live in
the files above: assertions in `GamePage`'s `verify*` methods, Canvas/Pixi mechanics in
`PixiController`, network mechanics (including the three mocked spin responses) in `ApiRequests`,
diagnostics in a private `PixiController` method.

## Fixtures

```ts
type Fixtures = {
  player: Player; // { nickname: string }
  game: GamePage; // app opened, game NOT started
  startedGame: GamePage; // game fixture + nickname entered + started + ready
};
```

- **`player`** creates a fresh `{ nickname: "player_<timestamp>" }` per test. The uniqueness is for
  session isolation (each test gets its own `?session=` query param, so balance/state never leaks
  between tests) — not for randomizing any outcome.
- **`game`** opens the application but does **not** start it. This exists specifically for tests
  that validate the start/onboarding flow itself — calling `start()`/`waitUntilReady()` from
  inside the fixture would make that flow untestable.
- **`startedGame`** depends on `game` and `player`: it enters the nickname, starts the game, and
  waits until the Pixi scene reports ready, then hands the same `GamePage` to the test. It does
  nothing beyond that — no mocking, no spinning, no unrelated setup.

## Why tests contain only business methods

`e2e/game.spec.ts` never calls `page.click`, `page.locator`, `page.mouse`, `page.route`, `expect`,
or `window.__TEST_APP__` directly. A test reads as a scenario:

```ts
test("player completes a winning spin", async ({ startedGame }) => {
  await startedGame.setNextSpinResult("win");
  await startedGame.spin();
  await startedGame.verifyResult("win");
});
```

The reasoning: a spec file is the one artifact non-automation stakeholders might actually read. If
it's full of coordinate math, route handlers, and raw `expect()` calls, it stops being readable as
a description of behavior. Every technical concern - how a click is computed, how a response is
mocked, what "won" actually means in terms of phase/balance/result/displayed text - has exactly
one home (`PixiController` or `GamePage`), so it's defined once and reused, not copy-pasted across
specs.

## Why assertions live inside GamePage, not the spec

`GamePage.verifyResult()`, `verifyApiError()`, etc. call Playwright's native `expect` internally.
There's no separate `GameAssertions` class and no generic wrappers like
`verifyVisible()`/`verifyEquals()` — each method expresses one specific business outcome (phase +
result + displayed text + balance checked together, not one implementation detail at a time).
`expect(await startedGame.getResult()).toBe('win')` in the spec would leak the _shape_ of a "win"
back into the test; `await startedGame.verifyResult('win')` doesn't.

## Typed Pixi label categories

Labels are grouped by what you can actually do with them, not one flat list mixing buttons, text,
and displays:

```ts
export const BUTTON_LABELS = ["spinButton", "betMinus", "betPlus"] as const;
export const TEXT_LABELS = ["balanceDisplay", "stateDisplay", "resultText"] as const;
export const DISPLAY_LABELS = ["reelsDisplay"] as const;

export type ButtonLabel = (typeof BUTTON_LABELS)[number];
export type TextLabel = (typeof TEXT_LABELS)[number];
export type DisplayLabel = (typeof DISPLAY_LABELS)[number];
export type PixiObjectLabel = ButtonLabel | TextLabel | DisplayLabel;
```

`PixiController.click()` only accepts a `ButtonLabel`; `getText()` only accepts a `TextLabel`.
Confirmed directly - both of these fail to typecheck:

```ts
pixi.click("resultText"); // Argument of type '"resultText"' is not assignable to '"spinButton" | "betMinus" | "betPlus"'
pixi.getText("spinButton"); // Argument of type '"spinButton"' is not assignable to '"balanceDisplay" | "stateDisplay" | "resultText"'
```

`GamePage` declares its own element surface at the top of the class from these categories -
`spinButton`/`betMinusButton`/`betPlusButton: ButtonLabel`, `balanceText`/`stateText`/`resultText:
TextLabel`, `reelsDisplay: DisplayLabel` - plus DOM selectors (`nicknameInputSelector`,
`startGameButtonSelector`, `canvasSelector`) for the two real HTML elements outside the canvas.
Methods reference `this.spinButton` etc. rather than repeating string literals, so the page's full
interactive surface is visible at a glance, the way a traditional Page Object declares its
selectors up front.

## Reading Pixi text

`balanceDisplay` and `stateDisplay` are `Container`s wrapping a private `Text` child with no prior
public accessor; `resultText` is itself a raw Pixi `Text`. The application now exposes a small
`.text` getter on the first two (mirroring the real `Text.text` property name) and a matching
bridge method, `getObjectText(label)`, that duck-types for a `.text` string at runtime - since
`namedObjects` is typed `Map<string, Container>` for `getObjectBounds()`'s sake, and `Container`
itself has no `.text`, this needed one narrow, explicitly-commented type assertion in the
application (not `any` - a runtime check against `unknown`). `PixiController.getText(label:
TextLabel)` wraps it with a clear error if the label doesn't resolve to readable text.

## How animation is actually detected

Before touching `spin()`, the application was inspected directly rather than assumed:

- `reelsDisplay` (the container) **never moves** during a spin - no x/y/scale/rotation/alpha
  change. Only its three private child `Text` objects have their `.text` mutated, every 80ms then
  200ms, until `spinAnimate()` settles them to the final symbols. So `phase === "spinning"` alone
  only proves the app's internal state flag flipped - not that anything is visually happening.
- The reel texts had no stable individual labels and weren't exposed anywhere. The smallest
  read-only addition was a `getReelSymbols()` bridge method returning the three current symbols
  (backed by a new `ReelsDisplay.getSymbols()`), and `PixiController.getReelSymbols()`/
  `waitForReelChange(previous)` to read and poll it.

`spin()` proves both boundaries explicitly:

```ts
async spin(): Promise<void> {
  this.balanceBeforeSpin = (await this.pixi.getSnapshot()).balance;
  const reelsBeforeClick = await this.pixi.getReelSymbols();

  await this.pixi.click("spinButton");
  await this.pixi.waitForPhase("spinning"); // app state says spinning
  await this.pixi.waitForReelChange(reelsBeforeClick); // reels actually changed
  await this.pixi.waitWhilePhase("spinning"); // spinning has genuinely ended
}
```

This is a real, enforced requirement, not a comment: an earlier version that hardcoded a wait for
`"result"` specifically (instead of "no longer spinning") **failed exactly as it should** when
applied to a mocked API error - `GameApp.ts`'s catch block calls no `spinAnimate()` at all, so the
error path can resolve faster than a single bridge round-trip can even observe `"spinning"`. That
confirmed there's genuinely no animation to prove on that path, so triggering an error uses
`spinExpectingError()` instead - a plain click with no animation assertion, synchronizing on
`"error"` directly via `verifyApiError()`.

No `animation` `GamePhase` was invented, and no `ANIMATION_LABELS` category was added - animation
is a real property change on real objects (the reel texts), observed with the same
`getReelSymbols()`/`waitForReelChange()` pair used everywhere else, not a new abstraction layer.

## PixiController and coordinate conversion

`PixiController` is the **only** Pixi/Canvas-specific code in this project:

```ts
class PixiController {
  async waitUntilReady(): Promise<void>;
  async click(label: ButtonLabel): Promise<void>;
  async getBounds(label: PixiObjectLabel): Promise<PixiObjectBounds>;
  async getObjectBoundsByRuntimeLabel(label: string): Promise<PixiObjectBounds>; // diagnostics only, see below
  async getText(label: TextLabel): Promise<string>;
  async getReelSymbols(): Promise<ReelSymbols>; // readonly [string, string, string]
  async getSnapshot(): Promise<GameSnapshot>;
  async waitForPhase(phase: GamePhase): Promise<void>;
  async waitWhilePhase(phase: GamePhase): Promise<void>; // resolves once phase is no longer `phase`
  async waitForReelChange(previous: ReelSymbols): Promise<void>;
}
```

The game has exactly three reel positions, never an arbitrary-length list, so `ReelSymbols` is a
`readonly [string, string, string]` tuple rather than `string[]`. The bridge itself still returns a
plain `string[]` (it's the application's own untyped contract), so `getReelSymbols()` checks the
length at runtime and throws `Expected exactly 3 reel symbols, received <count>` on a mismatch,
rather than casting an arbitrary array straight to the tuple.

`getObjectBoundsByRuntimeLabel()` exists for exactly one caller:
`verifyUnknownObjectDiagnostics()`, which needs to prove the diagnostic error message for a label
that (by definition) isn't a valid `PixiObjectLabel` - so it can't be expressed as one without an
unsafe cast. Rather than widen `getBounds()`/`click()`/`getText()` to accept `string` (which would
let a typo like `pixi.click("spinbutton")` compile everywhere), this one small, explicitly-named
method is the only place a raw runtime string is accepted, and it shares its implementation with
the typed `getBounds()` internally.

`getObjectBounds()` returns bounds in **render space** (`canvas.width`/`canvas.height` pixel
space, already resolved for anchor/pivot/scale/nested transforms by the application's own Pixi
`getBounds()` call). `getBounds()` validates those bounds against the canvas's actual render
resolution - **not** its CSS bounding rect, which can differ under CSS scaling or a different
device pixel ratio. `click()` then converts to a real browser click:

```ts
const rect = canvas.getBoundingClientRect();
const scaleX = rect.width / canvas.width;
const scaleY = rect.height / canvas.height;

const renderX = bounds.x + bounds.width / 2;
const renderY = bounds.y + bounds.height / 2;

const browserX = rect.left + renderX * scaleX;
const browserY = rect.top + renderY * scaleY;

await page.mouse.click(browserX, browserY);
```

No magic coordinates anywhere - every click is computed from live bounds at the moment the test
runs. `verifyScaledCanvasInteraction()` proves the whole chain - bounds validation, coordinate
conversion, the real click, and the complete animation lifecycle - still holds when the canvas is
displayed at half its render resolution via CSS, by simply calling `spin()` after resizing it.

## Strong typing

`window.__TEST_APP__` is typed once, in `types/pixi.types.ts`, via a global `Window` interface
augmentation - no `as any` casts scattered through the code:

```ts
interface TestBridge {
  isReady(): boolean;
  getObjectBounds(label: string): PixiObjectBounds | null;
  getObjectText(label: string): string | null;
  getReelSymbols(): string[];
  getGameSnapshot(): GameSnapshot;
}

declare global {
  interface Window {
    __TEST_APP__?: TestBridge;
  }
}
```

`types/game.types.ts` holds the business/domain model (`GamePhase`, `GameResult`, `SpinMockResult`,
`Player`, `ReelSymbols`, `SpinOutcome`, `SpinApiResponse`, `SpinHttpResult`, `GameSnapshot`);
`types/pixi.types.ts` holds Pixi/Canvas-specific concepts (the label categories, `PixiObjectBounds`)
plus the bridge contract itself. `GameResult` (`'win' | 'loss'`) is `verifyResult()`'s parameter
type; `SpinMockResult` (`GameResult | 'error'`) is wider, since `setNextSpinResult()` can also
simulate a failed request that isn't a "result" in the same sense. `SpinApiResponse` is an alias of
`SpinOutcome` - the real, unmocked `/api/game/spin` response body is the same contract the mocked
path already models, so it isn't redefined; `SpinHttpResult` pairs it with the captured HTTP status
for `GamePage.spinWithRealApi()`/`verifyRealSpinResponse()`. `GameSnapshot` keeps the real
`betAmount` and full `{win, amount, symbols}` `lastResult` shape (rather than collapsing it to a
bare string) because exact balance-arithmetic verification is real, existing coverage - it does
**not** duplicate displayed text (no `resultText` field); that's read
separately via `getText()`, which is the more precise, reusable place for it.

## ApiRequests: network mechanics

`support/ApiRequests.ts` is the only network-specific code in this project: the spin endpoint,
response observation, deterministic mocking, and turning raw JSON into typed results. It knows
nothing about Pixi/Canvas or business rules - `GamePage` owns those.

```ts
class ApiRequests {
  readonly spinEndpoint: string;
  waitForSpinResponse(): Promise<Response>;
  async readSpinResponse(response: Response): Promise<SpinHttpResult>;
  async mockNextSpin(result: SpinMockResult): Promise<void>;
}
```

### Deterministic mocking

```ts
await startedGame.setNextSpinResult("win"); // | "loss" | "error"
```

`GamePage.setNextSpinResult()` delegates straight to `ApiRequests.mockNextSpin()`, which
intercepts `spinEndpoint` with `page.route()` and a fixed, typed response body - the same mechanism
a test would use against any real backend. There's no `Math.random()` patching and no
`forceWin()`-style shortcut on the bridge.

**This is deliberately a true one-shot mock.** `page.route()` does not replace a previously
registered handler for the same pattern - each call stacks a new one, and only the most recently
registered handler runs (confirmed directly: an "older" handler that isn't superseded is still
reachable via `route.fallback()`). The handler unroutes itself immediately after fulfilling -
fulfill first, then unroute, since unrouting first makes Playwright auto-resolve the route and the
subsequent `fulfill()` throws `"Route is already handled!"`. That makes `mockNextSpin()` apply to
exactly one request no matter how many times it's called in a test, rather than leaving every prior
handler registered and merely shadowed.

### Real network flow

```ts
await startedGame.spinWithRealApi();
await startedGame.verifyRealSpinResponse();
```

Action and verification stay separate. `spinWithRealApi()` calls `ApiRequests.waitForSpinResponse()`
_before_ the real Pixi click - a fast response could otherwise resolve before Playwright starts
listening for it - clicks, then hands the raw response to `ApiRequests.readSpinResponse()` and
stores the typed result; it contains no assertions. `readSpinResponse()` parses `response.json()`
against a runtime type guard and throws if the shape doesn't match, rather than trusting `unknown`
JSON. `verifyRealSpinResponse()` then checks only what parsing alone can't guarantee: the HTTP
status, and that the real backend's `win`/`amount` fields actually agree - confirmed by reading
both the app's dev-server mock and its Vercel serverless function: `win` is true exactly when
`amount > 0`.

## State synchronization

No `waitForTimeout()`, no manual `sleep()`, no arbitrary delays. Tests rely on:

- Playwright's built-in auto-waiting for DOM actions;
- `ApiRequests.waitForSpinResponse()` for a real (unmocked) network round trip;
- `expect.poll()` inside `PixiController.waitForPhase()`/`waitWhilePhase()`/`waitForReelChange()`;
- `page.waitForFunction()` to wait for the bridge to attach and report ready.

The spec never knows any of this is happening - it just calls `spin()` and `verifyResult()`. See
[How animation is actually detected](#how-animation-is-actually-detected) above for what `spin()`
does internally.

## Scenarios

12 tests, all under one `test.describe("Pixi.js game", ...)` in `e2e/game.spec.ts`:

**Business flow** — a player can start the game (nickname reaches the bridge, phase reaches
`ready`); the Spin button resolves via its stable Pixi label with valid, visible, renderable
bounds; the reels display is visible on the game board; the bet amount can be adjusted with the
real bet buttons; a winning spin and a losing spin each let `spin()` prove the full animation
lifecycle (phase reaches `"spinning"`, the reel symbols genuinely change, phase leaves
`"spinning"`) before `verifyResult()` checks the settled phase + structured result + **actual
displayed Pixi text** + exact balance arithmetic; a failed spin (triggered via
`spinExpectingError()`, since the real error path has no animation to prove) refunds the bet, shows
the real error text, and the game is genuinely spinnable again immediately afterward (proven by
completing a real subsequent win, not just checking the error went away); a repeated click while
already spinning doesn't deduct the bet twice.

**Technical regressions** — real coverage that doesn't read naturally as business behavior, using
equally meaningful method names rather than forced business language: an unknown Pixi object
throws a diagnosable error (requested label, canvas internal/CSS dimensions, current phase, known
labels - never the whole Pixi stage); the Spin button remains clickable - including a full spin -
when the canvas is CSS-scaled to half its render resolution; the Spin button's bounds stay stable
across a full spin cycle; a real, unmocked request reaches `/api/game/spin` (see [Real network
flow](#real-network-flow)).

One scenario from an earlier version of this project - a test proving DOM selectors can't find the
Spin button - was intentionally dropped rather than ported. It didn't verify application
correctness, only a structural fact about Canvas rendering that every other test already
demonstrates implicitly (they all interact through `PixiController`, never a DOM selector).

## Running locally

**Prerequisites:** Node.js 22+, and a running instance of the application from
[pixijs-e2e-testing-demo](https://github.com/testomut/pixijs-e2e-testing-demo) (clone it
separately and run `npm run dev --prefix demo-app`, or point at any reachable instance).

```bash
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test              # expects the app at http://localhost:3000 by default
```

Point tests at a different instance (e.g. a locally different port, or - for manual, non-CI
exploration only - the deployed demo) with:

```bash
APP_BASE_URL=https://pixijs-e2e-testing-demo.vercel.app npm test
```

## Commands

| Command                | What it does                                                             |
| ---------------------- | ------------------------------------------------------------------------ |
| `npm run lint`         | ESLint                                                                   |
| `npm run format:check` | Prettier check                                                           |
| `npm run typecheck`    | `tsc --noEmit`                                                           |
| `npm test`             | Runs the Playwright suite against `APP_BASE_URL`                         |
| `npm run test:ui`      | Playwright's interactive UI mode                                         |
| `npm run test:headed`  | Runs headed, for local debugging                                         |
| `npm run test:video`   | Same suite, records video for every test (not just failures) — see below |
| `npm run test:report`  | Opens the last HTML report                                               |

## Video recording

Two distinct use cases, handled differently:

**`npm test` (also what CI runs)** — diagnostic video only. `playwright.config.ts` sets
`video: "retain-on-failure"`, so a passing test keeps no video and a failing one does. This is what
CI uploads as a failure artifact (see [CI](#ci-why-a-local-checkout-not-the-deployed-demo)); it is
not meant to produce anything worth watching for its own sake.

**`npm run test:video`** — sets `RECORD_VIDEO=true` (cross-platform via `cross-env`, no second
config file), which switches the same `video` option to `"on"`, so every test - including passing
ones - gets a recording under `test-results/<test name>/video.webm`. This is how the curated demo
clip below was produced: run it, then deliberately pick and copy one good recording - the command
itself doesn't select or commit anything automatically.

This is also why generated video only shows up locally or on CI's failure runs, never both: CI
never sets `RECORD_VIDEO`, so a normal CI run - success or failure - never pays the cost of
recording every test, only the ones that actually fail.

**Generated artifact vs. committed demo** - `test-results/` and `playwright-report/` are gitignored
(temporary, regenerated every run); `docs/assets/pixi-e2e-demo.webm` is the one deliberately
selected, permanently committed exception - not covered by any wildcard `.webm` ignore rule.

## CI: why a local checkout, not the deployed demo

Two options were considered for how CI reaches the application:

- **(A) Test the deployed Vercel demo.** Simplest to wire up, but ties every CI run to whatever
  happens to be currently deployed - which has lagged behind the application repo's `main` branch
  before. It also adds a real network dependency and couples this repo's CI to Vercel's uptime.
- **(B) Check out the application repository and start it locally.** Slightly more setup, but
  tests the actual current application source, deterministically, on every run.

**(B) was chosen.** `.github/workflows/e2e.yml` checks out `testomut/pixijs-e2e-testing-demo` into
`app/`, installs `app/demo-app`, starts it with `npm run dev` (the mocked `/api/game/spin`
endpoint is Vite dev-server middleware, not present in a `vite preview` static build), waits for
it to respond, then runs this repo's lint/format/typecheck/Playwright suite against it. `app/` is
excluded from this project's ESLint/Prettier/TypeScript configs, since it's the application repo's
own code, not this project's.

## Diagnostics

- **Screenshots**, **video**, and **trace** all retained on failure (`retain-on-failure`, so a
  first-attempt local failure with 0 retries still gets a trace) - all uploaded as CI artifacts.
  See [Video recording](#video-recording) for the separate `test:video` path used only to produce
  the curated demo clip, never run in CI.
- `PixiController` errors include the requested label, canvas internal dimensions, canvas CSS
  dimensions, the current game phase, and the object bounds where available - never the whole Pixi
  stage.
- `npm run test:report` opens the HTML report locally after a run.

## Limitations

- This repository owns no application code - if the bridge shape or object labels change in
  `pixijs-e2e-testing-demo`, `types/pixi.types.ts` and `PixiController`'s known-label list here
  need to be updated by hand; nothing enforces that they stay in sync.
- CI always tests the application repository's current `main`, not a pinned version - a breaking
  change there can break this repo's CI without a corresponding change here.
- `workers: 1` in `playwright.config.ts`: several headless WebGL contexts competing for a software
  renderer under CI/sandbox constraints produced GPU-stall timeouts unrelated to test correctness,
  observed directly while building this suite.
- The CSS-scaling test covers CSS-size scaling specifically, not device-pixel-ratio scaling, since
  the application doesn't currently vary DPR.
- No Cypress equivalent exists in this repository by design - Cypress automation for this
  application is a separate, not-yet-created repository.

## License

MIT
