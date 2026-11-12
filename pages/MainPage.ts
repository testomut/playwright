import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class MainPage extends BasePage {
  readonly pageUrl = '/wiki/Main_Page';

  constructor(page: Page) {
    super(page);
  }
}
