import { test as base } from '@playwright/test';
import { QuizPage } from './pages/QuizPage';

type Fixtures = {
  quizPage: QuizPage;
};

export const test = base.extend<Fixtures>({
  quizPage: async ({ page }, use) => {
    const quizPage = new QuizPage(page);
    await quizPage.open();
    await use(quizPage);
  },
});
