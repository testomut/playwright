# Charlie quiz test

Playwright test for the Charlie registration flow:

1. Complete the quiz.
2. Register a user.
3. Book a trial lesson.
4. Verify the user and lesson creation requests.
5. Verify the trial lesson on the dashboard.

## Run

```powershell
npm install
npm run install:browsers
Copy-Item .env.example .env
npm test
```

Set a controlled phone number in `.env`. The test creates a user and a trial lesson on stage.

## Demo

[Playwright test run](docs/playwright-test-run.webm)

To check a known quiz variant with eight question steps, change the test call to:

```ts
await quizPage.passQuiz(8);
```
