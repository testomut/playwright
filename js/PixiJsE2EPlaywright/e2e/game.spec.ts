import { test } from "../fixtures/game.fixture.js";

test.describe("Pixi.js game", () => {
  test("player can start the game", async ({ game, player }) => {
    await game.start(player.nickname);
    await game.waitUntilReady();
    await game.verifyPlayer(player.nickname);
    await game.verifyReady();
  });

  test("the Spin button can be located semantically", async ({ startedGame }) => {
    await startedGame.verifySpinButtonIsInteractable();
  });

  test("the reels display is visible on the game board", async ({ startedGame }) => {
    await startedGame.verifyReelsDisplayIsVisible();
  });

  test("the bet amount can be adjusted with the bet buttons", async ({ startedGame }) => {
    await startedGame.increaseBet();
    await startedGame.verifyBetAmount(15);
    await startedGame.decreaseBet();
    await startedGame.verifyBetAmount(10);
  });

  test("player completes a winning spin", async ({ startedGame }) => {
    await startedGame.setNextSpinResult("win");
    await startedGame.spin();
    await startedGame.verifyResult("win");
  });

  test("player completes a losing spin", async ({ startedGame }) => {
    await startedGame.setNextSpinResult("loss");
    await startedGame.spin();
    await startedGame.verifyResult("loss");
  });

  test("player sees an API error and can spin again afterward", async ({ startedGame }) => {
    await startedGame.setNextSpinResult("error");
    await startedGame.spinExpectingError();
    await startedGame.verifyApiError();

    // A fresh mocked response proves the game is genuinely usable again,
    // not just reporting "error" while still stuck.
    await startedGame.setNextSpinResult("win");
    await startedGame.spin();
    await startedGame.verifyResult("win");
  });

  test("a repeated spin click while already spinning is ignored", async ({ startedGame }) => {
    await startedGame.setNextSpinResult("loss");
    await startedGame.verifyRepeatedSpinIsIgnored();
  });

  test("an unknown Pixi object produces a diagnosable failure", async ({ startedGame }) => {
    await startedGame.verifyUnknownObjectDiagnostics();
  });

  test("the Spin button remains clickable when the canvas is CSS-scaled", async ({
    startedGame,
  }) => {
    await startedGame.setNextSpinResult("loss");
    await startedGame.verifyScaledCanvasInteraction();
  });

  test("the Spin button's position stays stable across a spin cycle", async ({ startedGame }) => {
    await startedGame.setNextSpinResult("loss");
    await startedGame.verifyButtonPositionStableAcrossSpin();
  });

  test("a real request reaches /api/game/spin", async ({ startedGame }) => {
    await startedGame.spinWithRealApi();
    await startedGame.verifyRealSpinResponse();
  });
});
