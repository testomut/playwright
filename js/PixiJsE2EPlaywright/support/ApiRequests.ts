import type { Page, Response, Route } from "@playwright/test";
import type { SpinApiResponse, SpinHttpResult, SpinMockResult } from "../types/game.types.js";

// Deterministic response bodies for mockNextSpin() - small and specific
// enough to live here rather than in a separate data module.
const SPIN_RESPONSES: Record<SpinMockResult, { status: number; body?: SpinApiResponse }> = {
  win: { status: 200, body: { win: true, amount: 100, symbols: ["💎", "💎", "💎"] } },
  loss: { status: 200, body: { win: false, amount: 0, symbols: ["🍒", "🍋", "⭐"] } },
  error: { status: 500 },
};

/**
 * Runtime contract check for a real (unmocked) spin response -
 * response.json() is unknown data, so its shape can't be assumed from
 * SpinApiResponse's compile-time type alone.
 */
function isSpinApiResponse(value: unknown): value is SpinApiResponse {
  const record = value as { win?: unknown; amount?: unknown; symbols?: unknown } | null;
  return (
    !!record &&
    typeof record.win === "boolean" &&
    typeof record.amount === "number" &&
    Array.isArray(record.symbols) &&
    record.symbols.length === 3 &&
    record.symbols.every((symbol) => typeof symbol === "string")
  );
}

/**
 * All Playwright-specific network interaction for the application's API:
 * response observation, deterministic mocking, and turning raw JSON into
 * typed results. Knows nothing about Pixi/Canvas or business rules -
 * GamePage owns those.
 */
export class ApiRequests {
  // API endpoints
  public readonly spinEndpoint: string = "/api/game/spin";

  constructor(private readonly page: Page) {}

  waitForSpinResponse(): Promise<Response> {
    return this.page.waitForResponse((response) => response.url().includes(this.spinEndpoint));
  }

  async readSpinResponse(response: Response): Promise<SpinHttpResult> {
    const body: unknown = await response.json();
    if (!isSpinApiResponse(body)) {
      throw new Error(
        `Invalid spin API response: expected { win: boolean, amount: number, symbols: [string, string, string] }, got ${JSON.stringify(body)}`,
      );
    }
    return { status: response.status(), body };
  }

  /**
   * page.route() stacks handlers rather than replacing them, so the
   * handler must unroute itself after fulfilling (not before - unrouting
   * first makes Playwright auto-resolve the route and fulfill() throws).
   * That's what makes this apply to exactly one request.
   */
  async mockNextSpin(result: SpinMockResult): Promise<void> {
    const response = SPIN_RESPONSES[result];
    const pattern = `**${this.spinEndpoint}`;
    const handler = async (route: Route) => {
      await route.fulfill({
        status: response.status,
        contentType: "application/json",
        body: JSON.stringify(response.body ?? { error: "mocked failure" }),
      });
      await this.page.unroute(pattern, handler);
    };
    await this.page.route(pattern, handler);
  }
}
