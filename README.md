# Playwright projects

Test automation projects built with Playwright, grouped by language. Each folder is a complete, independent
project with its own dependencies and README; they were moved here from separate repositories with their full
commit history.

## JavaScript / TypeScript (`js/`)

| Project | What it shows |
|---|---|
| [playwrightQaseTests](js/playwrightQaseTests) | Framework architecture sample: Page Objects, composable fixtures, API-assisted setup and teardown, parallel-safe accounts, Qase reporting |
| [PixiJsE2EPlaywright](js/PixiJsE2EPlaywright) | E2E automation of a Pixi.js / Canvas game: semantic object discovery, coordinate conversion, deterministic API mocking ([demo app](https://github.com/testomut/pixijs-e2e-testing-demo)) |
| [CasinoAutoOauthPlaywright](js/CasinoAutoOauthPlaywright) | Authentication flows: Page Objects, fixtures, generated test data, test-case documentation, reporting |
| [WikiAutoTestsPlaywright](js/WikiAutoTestsPlaywright) | Wikipedia scenarios, the Playwright counterpart of a [Cypress reference project](https://github.com/testomut/WikiAutoTestsCypress) |
| [allright-qa-automation](js/allright-qa-automation) | E2E automation of a registration and trial-lesson booking flow |
| [wikipedia-language-aqa](js/wikipedia-language-aqa) | Test task: an authorised user switches the Wikipedia interface language; UI steps plus a MediaWiki API check that the preference is persisted, runs in Docker |

## Python (`python/`)

| Project | What it shows |
|---|---|
| [python-playwright-qa-framework](python/python-playwright-qa-framework) | pytest + Playwright: layered fixtures, API seeding and cleanup, Pydantic models, xdist worker isolation, offline CI checks |

## Running a project

Open its folder and follow its README, for example:

```sh
cd js/playwrightQaseTests && npm ci && npx playwright install && npx playwright test
cd python/python-playwright-qa-framework && pip install -r requirements.txt && pytest
```

The CI workflow files of each project are kept in its folder as they were; GitHub runs workflows only from the
repository root, so they document how each suite runs in CI rather than run here.

## Related repositories

- [api-test-agent](https://github.com/testomut/api-test-agent) - CLI that audits OpenAPI specs and generates reviewable Playwright API tests
- [PixiJsE2ECypress](https://github.com/testomut/PixiJsE2ECypress), [WikiAutoTestsCypress](https://github.com/testomut/WikiAutoTestsCypress) - Cypress counterparts
