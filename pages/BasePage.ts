import { Locator, Page, expect } from '@playwright/test';

export abstract class BasePage {
  abstract readonly pageUrl: string;

  readonly html: Locator;
  readonly heading: Locator;
  readonly userPageLink: Locator;
  readonly userMenuToggle: Locator;
  readonly preferencesLink: Locator;

  constructor(protected readonly page: Page) {
    this.html = page.locator('html');
    this.heading = page.locator('#firstHeading');
    this.userPageLink = page.locator('#pt-userpage-2 a, #pt-userpage a').first();
    this.userMenuToggle = page.locator('#vector-user-links-dropdown-checkbox');
    this.preferencesLink = page.locator('#pt-preferences a');
  }

  async open(): Promise<void> {
    await this.navigate(this.pageUrl);
  }

  protected async navigate(path: string, expectedUrl?: RegExp | string): Promise<void> {
    await this.page.goto(path);
    if (expectedUrl) {
      await this.expectUrl(expectedUrl);
    }
  }

  private async prepareElement(locator: Locator): Promise<void> {
    await this.expectVisible(locator);
    await this.expectEnabled(locator);
  }

  protected async customClick(locator: Locator): Promise<void> {
    await this.prepareElement(locator);
    await locator.click();
  }

  protected async customFill(locator: Locator, value: string): Promise<void> {
    await this.prepareElement(locator);
    await locator.fill(value);
  }

  protected async expectVisible(locator: Locator): Promise<void> {
    await expect(locator).toBeVisible();
  }

  protected async expectEnabled(locator: Locator): Promise<void> {
    await expect(locator).toBeEnabled();
  }

  protected async expectDisabled(locator: Locator): Promise<void> {
    await expect(locator).toBeDisabled();
  }

  protected async expectAttribute(locator: Locator, name: string, value: string): Promise<void> {
    await expect(locator).toHaveAttribute(name, value);
  }

  protected async expectText(locator: Locator, text: string): Promise<void> {
    await expect(locator).toHaveText(text);
  }

  protected async expectUrl(url: RegExp | string): Promise<void> {
    await expect(this.page).toHaveURL(url);
  }

  async expectLoggedInAs(username: string): Promise<void> {
    await this.expectText(this.userPageLink, username);
  }

  async expectInterfaceLanguage(code: string): Promise<void> {
    await this.expectAttribute(this.html, 'lang', code);
  }

  async expectHeading(text: string): Promise<void> {
    await this.expectText(this.heading, text);
  }
}
