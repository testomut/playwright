import js from "@eslint/js";
import tseslint from "typescript-eslint";
import playwright from "eslint-plugin-playwright";
import prettier from "eslint-config-prettier";

export default tseslint.config(
  {
    // "app/" is where CI checks out the separate application repository
    // (see .github/workflows/e2e.yml) - it is not part of this project and
    // must never be linted with this project's rules.
    ignores: ["**/node_modules/**", "playwright-report/**", "test-results/**", "app/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { playwright },
    rules: {
      ...playwright.configs["flat/recommended"].rules,
      // Assertions live inside GamePage's verifyResult/verifyApiError/etc
      // methods, not as inline expect() calls in the spec.
      "playwright/expect-expect": ["warn", { assertFunctionPatterns: ["^verify[A-Z]"] }],
    },
  },
  prettier,
);
