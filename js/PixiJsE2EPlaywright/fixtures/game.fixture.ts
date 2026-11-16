import { test as baseTest } from "@playwright/test";
import { GamePage } from "../pages/GamePage.js";
import { PixiController } from "../support/PixiController.js";
import { ApiRequests } from "../support/ApiRequests.js";
import type { Player } from "../types/game.types.js";

type Fixtures = {
  player: Player;
  game: GamePage;
  startedGame: GamePage;
};

export const test = baseTest.extend<Fixtures>({
  // A fresh, readable nickname per test. The uniqueness is for session
  // isolation (see GamePage's session id), not for randomizing any
  // outcome - those come from setNextSpinResult().
  player: async ({}, use) => {
    await use({ nickname: `player_${Date.now()}` });
  },

  // Opens the app but does not start the game - needed by tests that
  // validate the start/onboarding flow itself.
  game: async ({ page }, use, testInfo) => {
    const pixi = new PixiController(page);
    const apiRequests = new ApiRequests(page);
    const gamePage = new GamePage(page, pixi, apiRequests, `test-${testInfo.testId}`);
    await gamePage.open();
    await use(gamePage);
  },

  // Builds on `game` + `player`: enters the nickname, starts the game,
  // and waits for the Pixi scene to be ready before handing it to the
  // test. Nothing beyond that happens here.
  startedGame: async ({ game, player }, use) => {
    await game.start(player.nickname);
    await game.waitUntilReady();
    await use(game);
  },
});

export { expect } from "@playwright/test";
