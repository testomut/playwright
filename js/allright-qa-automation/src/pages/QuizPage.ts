import { expect, Locator, Page, Response } from '@playwright/test';

const QUIZ_URL = '/uk/app/sign-up/long/charlie/age-range';
const USERS_API = '/api/v1/users';
const LESSONS_API = '/api/v1/lessons';
const DASHBOARD_URL = '/uk/app/dashboard';

const FORM_INPUTS = 'input:not([type="hidden"]), textarea';
const TEXT_INPUT = 'input:not([type="hidden"])';
const PHONE_INPUT = 'input[type="tel"]';

const NEXT_BUTTONS = ['Далі', 'Продовжити'];
const BOOK_BUTTON = 'Забронювати урок';
const SKIP_EMAIL = 'Пропустити';
const DAYS = ['Сьогодні', 'Завтра'];
const PERIODS = ['ранок', 'день', 'вечір'];
const TRIAL_LESSON = 'Пробний урок';
const CHILD_NAME = 'Test Child';
const PARENT_NAME = 'Test Parent';
const CHILD_NAME_INPUT = 'дитини';
const PARENT_OPTION = 'Я — мати або батько';
const LOAD_ERROR = 'Помилка завантаження';
const IGNORED_BUTTONS = [
  ...NEXT_BUTTONS,
  'Вимкнути звук відео',
  'Open Intercom Messenger',
  'Відкрити програму для спілкування Intercom',
];

export class QuizPage {
  private quizSteps = 0;
  private expectedQuizSteps?: number;
  private registrationResponse?: Response;
  private bookingResponse?: Response;

  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    for (let attempt = 0; attempt < 3; attempt++) {
      await this.page.goto(QUIZ_URL, { waitUntil: 'domcontentloaded' });
      await this.page.waitForTimeout(1_000);

      if (!(await this.page.getByText(LOAD_ERROR, { exact: true }).isVisible())) return;
    }

    throw new Error('Quiz failed to load after three attempts');
  }

  async passQuiz(expectedSteps?: number): Promise<void> {
    this.expectedQuizSteps = expectedSteps;
    let currentStep = '';
    const selectedAnswers = new Set<string>();

    for (let attempt = 0; attempt < 60; attempt++) {
      const step = await this.currentStep();
      if (step !== currentStep) {
        currentStep = step;
        selectedAnswers.clear();
      }

      const input = this.page.locator(FORM_INPUTS).filter({ visible: true });
      if (await input.count()) {
        const placeholder = (await input.first().getAttribute('placeholder')) ?? '';
        if (!placeholder.includes(CHILD_NAME_INPUT)) return;
        await input.first().fill(CHILD_NAME);
        await expect.poll(() => this.clickButton(NEXT_BUTTONS)).toBe(true);
        this.quizSteps++;
        continue;
      }

      if (await this.clickButton(NEXT_BUTTONS)) {
        this.quizSteps++;
        continue;
      }

      const answer = await this.firstAnswer(selectedAnswers);

      if (answer) {
        selectedAnswers.add((await answer.innerText()).trim());
        await answer.click({ timeout: 5_000 });
        await this.page.waitForTimeout(200);
      } else {
        throw new Error(`No actionable quiz control found at ${this.page.url()}`);
      }
    }

    throw new Error('Quiz did not reach the registration form within 60 interactions');
  }

  async checkQuizPassed(): Promise<void> {
    const registrationInput = this.page
      .locator(FORM_INPUTS)
      .filter({ visible: true })
      .first();

    await expect(registrationInput).toBeVisible();
    expect(this.quizSteps).toBeGreaterThan(0);
    if (this.expectedQuizSteps !== undefined) expect(this.quizSteps).toBe(this.expectedQuizSteps);
  }

  async register(phone: string): Promise<void> {
    const registration = this.waitForPost(USERS_API);

    await this.clickButton(PARENT_OPTION);
    await this.fillCurrentInput(PARENT_NAME);
    await this.clickButton(NEXT_BUTTONS);
    await this.fillPhone(phone);
    await this.clickButton(NEXT_BUTTONS);

    this.registrationResponse = await registration;

    await this.page.getByText(SKIP_EMAIL, { exact: true }).first().click();
  }

  async checkRegistration(): Promise<void> {
    expect(this.registrationResponse?.ok(), 'User was not created').toBe(true);
    await expect(this.page.getByRole('button', { name: BOOK_BUTTON, exact: true })).toBeVisible();
  }

  async bookTrialLesson(): Promise<void> {
    for (const day of [...DAYS].reverse()) {
      const dayOption = this.page.getByText(day, { exact: true }).first();
      if (await dayOption.isVisible()) {
        await dayOption.click();
        break;
      }
    }

    for (const period of PERIODS) {
      await this.clickButton(period);
      const times = this.page.getByRole('button');

      for (let index = 0; index < await times.count(); index++) {
        const time = times.nth(index);
        if (this.isTime(await time.innerText()) && (await this.isEnabled(time))) {
          await time.click();
          const booking = this.waitForPost(LESSONS_API);
          await this.page.getByRole('button', { name: BOOK_BUTTON, exact: true }).click();
          this.bookingResponse = await booking;
          return;
        }
      }
    }

    throw new Error('No available trial lesson slot');
  }

  async checkTrialLessonBooked(): Promise<void> {
    expect(this.bookingResponse?.ok(), 'Trial lesson was not booked').toBe(true);
    await expect.poll(() => this.page.url()).toContain(DASHBOARD_URL);
    await expect(this.page.getByText(TRIAL_LESSON).first()).toBeVisible();
  }

  private async firstAnswer(selectedAnswers: Set<string>): Promise<Locator | undefined> {
    const buttons = this.page.getByRole('button').filter({ visible: true });
    for (let index = 0; index < await buttons.count(); index++) {
      const button = buttons.nth(index);
      const text = (await button.innerText()).trim();
      if (
        text &&
        !selectedAnswers.has(text) &&
        !IGNORED_BUTTONS.includes(text) &&
        (await this.isEnabled(button))
      ) return button;
    }
  }

  private async currentStep(): Promise<string> {
    const progress = this.page.getByText(/^\d+\s*\/\s*\d+$/).first();
    return (await progress.textContent().catch(() => '')) ?? '';
  }

  private async fillCurrentInput(value: string): Promise<void> {
    await this.page.locator(TEXT_INPUT).filter({ visible: true }).first().fill(value);
  }

  private async fillPhone(phone: string): Promise<void> {
    const input = this.page.locator(PHONE_INPUT).filter({ visible: true }).first();
    await input.fill('');
    await input.pressSequentially(phone, { delay: 20 });
  }

  private async clickButton(names: string | string[]): Promise<boolean> {
    for (const name of Array.isArray(names) ? names : [names]) {
      const button = this.page
        .getByRole('button', { name, exact: true })
        .filter({ visible: true })
        .first();
      if (!(await this.isEnabled(button))) continue;
      await button.click({ timeout: 5_000 });
      await this.page.waitForTimeout(300);
      return true;
    }
    return false;
  }

  private isTime(text: string): boolean {
    const [hours, minutes, rest] = text.trim().split(':');
    return rest === undefined && hours?.length === 2 && minutes?.length === 2 &&
      !Number.isNaN(Number(hours)) && !Number.isNaN(Number(minutes));
  }

  private async isEnabled(locator: Locator): Promise<boolean> {
    return (await locator.isVisible().catch(() => false)) && (await locator.isEnabled().catch(() => false));
  }

  private waitForPost(path: string): Promise<Response> {
    return this.page.waitForResponse(
      response => response.url().includes(path) && response.request().method() === 'POST',
    );
  }
}
