import { test } from '../src/fixtures';

test('user completes the quiz, registers and books a trial lesson', async ({ quizPage }) => {
  const phone = process.env.TEST_PHONE;
  test.skip(!phone, 'TEST_PHONE is required');

  await quizPage.passQuiz();
  await quizPage.checkQuizPassed();

  await quizPage.register(phone!);
  await quizPage.checkRegistration();

  await quizPage.bookTrialLesson();
  await quizPage.checkTrialLessonBooked();
});
