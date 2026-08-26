import { test } from '../src/fixtures';

test('user completes the quiz, registers and books a trial lesson', async ({ quizPage }) => {
  const phoneTemplate = process.env.TEST_PHONE;
  test.skip(!phoneTemplate, 'TEST_PHONE is required');
  const phone = uniquePhone(phoneTemplate!);

  await quizPage.passQuiz();
  await quizPage.checkQuizPassed();

  await quizPage.register(phone);
  await quizPage.checkRegistration();

  await quizPage.bookTrialLesson();
  await quizPage.checkTrialLessonBooked();
});

function uniquePhone(template: string): string {
  const suffixLength = Math.min(7, template.replace(/\D/g, '').length);
  const suffix = `${Date.now()}`.slice(-suffixLength);
  let index = suffix.length - 1;

  return [...template].reverse().map(character => {
    if (/\d/.test(character) && index >= 0) return suffix[index--];
    return character;
  }).reverse().join('');
}
