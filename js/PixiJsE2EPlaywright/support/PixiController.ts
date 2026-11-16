import { expect, type Page } from "@playwright/test";
import type { GamePhase, GameSnapshot, ReelSymbols } from "../types/game.types.js";
import type {
  ButtonLabel,
  TextLabel,
  PixiObjectLabel,
  PixiObjectBounds,
} from "../types/pixi.types.js";
import { KNOWN_LABELS } from "../types/pixi.types.js";

const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * The only Pixi/Canvas-specific abstraction in this project: waiting for
 * the test bridge, resolving an object's real bounds into a browser
 * click, reading displayed text/reel state, and polling game phase.
 * Knows nothing about business outcomes like wins, losses, or balances -
 * that belongs to GamePage.
 */
export class PixiController {
  constructor(private readonly page: Page) {}

  async waitUntilReady(timeoutMs = DEFAULT_TIMEOUT_MS): Promise<void> {
    await this.page.waitForFunction(
      () => typeof window.__TEST_APP__ !== "undefined" && window.__TEST_APP__.isReady(),
      undefined,
      { timeout: timeoutMs },
    );
  }

  /**
   * Resolves a Pixi object's global bounds and validates them: finite,
   * and within the canvas's actual render resolution. Throws with the
   * requested label and current app state when the object can't be used.
   */
  async getBounds(label: PixiObjectLabel): Promise<PixiObjectBounds> {
    return this.resolveBounds(label);
  }

  /**
   * For labels that genuinely can't be known at compile time (e.g.
   * diagnosing a stage that has drifted from the known label list).
   * click()/getText()/getBounds() stay typed - don't reach for this
   * just to avoid the compiler.
   */
  async getObjectBoundsByRuntimeLabel(label: string): Promise<PixiObjectBounds> {
    return this.resolveBounds(label);
  }

  private async resolveBounds(label: string): Promise<PixiObjectBounds> {
    const canvasLocator = this.page.locator("canvas");
    const canvasCount = await canvasLocator.count();
    if (canvasCount === 0) {
      throw new Error(
        `Cannot resolve bounds for "${label}": no <canvas> element is attached to the page.`,
      );
    }

    // getObjectBounds() returns render-space bounds (canvas.width/height
    // pixel space), not CSS pixels - validate against the canvas's actual
    // render resolution, not its (possibly CSS-scaled) bounding rect.
    const canvasSize = await canvasLocator.evaluate((el: HTMLCanvasElement) => ({
      width: el.width,
      height: el.height,
    }));

    const bounds = await this.page.evaluate(
      (objectLabel) => window.__TEST_APP__?.getObjectBounds(objectLabel) ?? null,
      label,
    );

    if (!bounds) {
      const diagnostics = await this.describeFailure(label);
      throw new Error(`Pixi object "${label}" was not found on the stage.\n${diagnostics}`);
    }

    const values = [bounds.x, bounds.y, bounds.width, bounds.height];
    if (!values.every(Number.isFinite)) {
      throw new Error(
        `Pixi object "${label}" returned non-finite bounds: ${JSON.stringify(bounds)}`,
      );
    }

    if (
      bounds.x < 0 ||
      bounds.y < 0 ||
      bounds.x + bounds.width > canvasSize.width ||
      bounds.y + bounds.height > canvasSize.height
    ) {
      throw new Error(
        `Pixi object "${label}" bounds fall outside the canvas render size ` +
          `(${canvasSize.width}x${canvasSize.height}, bounds ${JSON.stringify(bounds)}).`,
      );
    }

    return bounds;
  }

  /**
   * The bridge returns render-space bounds; converting them into real
   * browser viewport coordinates before the pointer event is this
   * controller's responsibility, not the application's.
   */
  async click(label: ButtonLabel): Promise<void> {
    const bounds = await this.getBounds(label);

    if (!bounds.visible || !bounds.renderable) {
      throw new Error(`Pixi object "${label}" is not visible/renderable and cannot be clicked.`);
    }

    const canvasLocator = this.page.locator("canvas");
    const canvasBox = await canvasLocator.boundingBox();
    if (!canvasBox) {
      throw new Error(`Cannot click "${label}": no <canvas> element is attached to the page.`);
    }

    const canvas = await canvasLocator.evaluate((el: HTMLCanvasElement) => ({
      width: el.width,
      height: el.height,
    }));

    // Scale accounts for the canvas being displayed at a different CSS
    // size than its internal render resolution (responsive layouts, DPR).
    const scaleX = canvas.width > 0 ? canvasBox.width / canvas.width : 1;
    const scaleY = canvas.height > 0 ? canvasBox.height / canvas.height : 1;

    const renderX = bounds.x + bounds.width / 2;
    const renderY = bounds.y + bounds.height / 2;

    const browserX = canvasBox.x + renderX * scaleX;
    const browserY = canvasBox.y + renderY * scaleY;

    await this.page.mouse.click(browserX, browserY);
  }

  async getText(label: TextLabel): Promise<string> {
    const text = await this.page.evaluate(
      (objectLabel) => window.__TEST_APP__?.getObjectText(objectLabel) ?? null,
      label,
    );
    if (text === null) {
      const diagnostics = await this.describeFailure(label);
      throw new Error(`Pixi object "${label}" has no readable text.\n${diagnostics}`);
    }
    return text;
  }

  /**
   * The bridge returns a plain string[] (the application's own untyped
   * contract), so the length is checked at runtime rather than cast
   * straight to the tuple.
   */
  async getReelSymbols(): Promise<ReelSymbols> {
    const symbols = await this.page.evaluate(() => window.__TEST_APP__?.getReelSymbols() ?? []);
    if (symbols.length !== 3) {
      throw new Error(`Expected exactly 3 reel symbols, received ${symbols.length}`);
    }
    return [symbols[0], symbols[1], symbols[2]];
  }

  async getSnapshot(): Promise<GameSnapshot> {
    return this.page.evaluate(() => {
      if (!window.__TEST_APP__) {
        throw new Error("window.__TEST_APP__ is not available - has the game been started?");
      }
      return window.__TEST_APP__.getGameSnapshot();
    });
  }

  /** Polls the game phase using Playwright's own retrying assertion, not a fixed wait. */
  async waitForPhase(phase: GamePhase, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<void> {
    try {
      await expect
        .poll(() => this.getSnapshot().then((snapshot) => snapshot.phase), { timeout: timeoutMs })
        .toBe(phase);
    } catch (error) {
      const diagnostics = await this.describeFailure();
      throw new Error(`Timed out waiting for phase "${phase}".\n${diagnostics}`, {
        cause: error,
      });
    }
  }

  /**
   * Polls until the game phase is no longer `phase` - the symmetric
   * counterpart to waitForPhase(), used to detect that a phase has
   * finished without assuming which phase it settles into next (e.g. a
   * spin can end in either "result" or "error").
   */
  async waitWhilePhase(phase: GamePhase, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<void> {
    try {
      await expect
        .poll(() => this.getSnapshot().then((snapshot) => snapshot.phase), { timeout: timeoutMs })
        .not.toBe(phase);
    } catch (error) {
      const diagnostics = await this.describeFailure();
      throw new Error(`Timed out waiting to leave phase "${phase}".\n${diagnostics}`, {
        cause: error,
      });
    }
  }

  /**
   * Proof that the spin animation is genuinely progressing visually,
   * not just that a phase flag flipped.
   */
  async waitForReelChange(previous: ReelSymbols, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<void> {
    try {
      await expect.poll(() => this.getReelSymbols(), { timeout: timeoutMs }).not.toEqual(previous);
    } catch (error) {
      const diagnostics = await this.describeFailure();
      throw new Error(
        `Timed out waiting for reel symbols to change from ${JSON.stringify(previous)}.\n${diagnostics}`,
        { cause: error },
      );
    }
  }

  private async describeFailure(label?: string): Promise<string> {
    const canvasLocator = this.page.locator("canvas");
    const canvasBox = await canvasLocator.boundingBox().catch(() => null);
    const canvasSize = await canvasLocator
      .evaluate((el: HTMLCanvasElement) => ({ width: el.width, height: el.height }))
      .catch(() => null);
    const snapshot = await this.page
      .evaluate(() => window.__TEST_APP__?.getGameSnapshot() ?? null)
      .catch(() => null);

    return [
      label ? `requested label: ${label}` : null,
      `canvas internal dimensions: ${JSON.stringify(canvasSize)}`,
      `canvas CSS dimensions: ${JSON.stringify(canvasBox)}`,
      `current game phase: ${snapshot?.phase ?? "unknown"}`,
      `game snapshot: ${JSON.stringify(snapshot)}`,
      `known object labels: ${KNOWN_LABELS.join(", ")}`,
    ]
      .filter((line) => line !== null)
      .join("\n");
  }
}
