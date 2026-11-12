import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { MainPage } from '../pages/MainPage';
import { PreferencesPage } from '../pages/PreferencesPage';
import { WikiApi } from '../utils/WikiApi';

export const DEFAULT_LANGUAGE = 'en';

type Credentials = { username: string; password: string };

type Fixtures = {
  credentials: Credentials;
  loginPage: LoginPage;
  mainPage: MainPage;
  preferencesPage: PreferencesPage;
  wikiApi: WikiApi;
  userSession: string;
  defLang: string;
};

export const test = base.extend<Fixtures>({
  credentials: async ({ }, use) => {
    const username = process.env.WIKI_USERNAME;
    const password = process.env.WIKI_PASSWORD;
    if (!username || !password) {
      throw new Error('WIKI_USERNAME and WIKI_PASSWORD must be set (see .env.example).');
    }
    await use({ username, password });
  },
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  mainPage: async ({ page }, use) => {
    await use(new MainPage(page));
  },
  preferencesPage: async ({ page }, use) => {
    await use(new PreferencesPage(page));
  },
  wikiApi: async ({ page }, use) => {
    await use(new WikiApi(page.request));
  },
  userSession: async ({ loginPage, credentials }, use) => {
    await test.step(`Precondition: log in as "${credentials.username}"`, async () => {
      await loginPage.open();
      await loginPage.login(credentials.username, credentials.password);
    });

    await use(credentials.username);
  },
  defLang: async ({ wikiApi }, use) => {
    try {
      await test.step(
        `Precondition: reset interface language to "${DEFAULT_LANGUAGE}" via API`,
        async () => {
          await wikiApi.setOption('language', DEFAULT_LANGUAGE);
        },
      );

      await use(DEFAULT_LANGUAGE);
    } finally {
      await test.step(
        `Teardown: restore interface language to "${DEFAULT_LANGUAGE}" via API`,
        async () => {
          await wikiApi.setOption('language', DEFAULT_LANGUAGE).catch(() => undefined);
        },
      );
    }
  },
});

const originalStep = test.step.bind(test);
test.step = ((
  title: string,
  body: () => Promise<unknown>,
  options?: { box?: boolean; timeout?: number },
) => {
  console.log(`[STEP] Starting: ${title}`);
  return originalStep(title, body, options);
}) as typeof test.step;

export { expect } from '@playwright/test';


