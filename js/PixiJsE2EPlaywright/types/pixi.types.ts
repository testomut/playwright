import type { GameSnapshot } from "./game.types.js";

// Labels grouped by actual responsibility, confirmed against the
// application source (testomut/pixijs-e2e-testing-demo) - not every
// decorative sprite, and not one flat list mixing unrelated categories.
export const BUTTON_LABELS = ["spinButton", "betMinus", "betPlus"] as const;
export const TEXT_LABELS = ["balanceDisplay", "stateDisplay", "resultText"] as const;
export const DISPLAY_LABELS = ["reelsDisplay"] as const;

export type ButtonLabel = (typeof BUTTON_LABELS)[number];
export type TextLabel = (typeof TEXT_LABELS)[number];
export type DisplayLabel = (typeof DISPLAY_LABELS)[number];

export type PixiObjectLabel = ButtonLabel | TextLabel | DisplayLabel;

export const KNOWN_LABELS = [
  ...BUTTON_LABELS,
  ...TEXT_LABELS,
  ...DISPLAY_LABELS,
] as const satisfies readonly PixiObjectLabel[];

export interface PixiObjectBounds {
  x: number;
  y: number;
  width: number;
  height: number;
  visible: boolean;
  renderable: boolean;
}

// The application-owned, read-only observability bridge. Mirrored here
// because the application and this project are separate repositories -
// this is the one copy this project's code relies on.
export interface TestBridge {
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
