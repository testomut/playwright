import { Locator, Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  readonly pageUrl = '/w/index.php?title=Special:UserLogin&returnto=Main_Page&usesul3=0';
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;

  constructor(page: Page) {
    super(page);
    this.usernameInput = page.locator('#wpName1');
    this.passwordInput = page.locator('#wpPassword1');
    this.loginButton = page.locator('#wpLoginAttempt');
  }

  override async open(): Promise<void> {
    await super.open();
    if ((await this.usernameInput.count()) === 0) {
      await super.open();
    }
  }

  async login(username: string, password: string): Promise<void> {
    await this.customFill(this.usernameInput, username);
    await this.customFill(this.passwordInput, password);
    await this.customClick(this.loginButton);
    await this.expectUrl(/\/wiki\/Main_Page/);
  }
}
