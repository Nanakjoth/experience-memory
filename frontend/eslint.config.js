// ESLint flat config (ESLint 9+). Run with: npm run lint
//
// Scope: correctness rules only. There is deliberately NO style/formatting
// config here — `tsc` already enforces unused symbols via noUnusedLocals and
// noUnusedParameters, and formatting is a separate concern (Prettier or an
// editor). Mixing the two usually produces noisy, low-value churn.

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["dist", "node_modules", "coverage"],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,

  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // Only components may export components. lib/appstate.tsx exports a
      // provider + a hook together, which is the documented React pattern, so
      // the rule is scoped to files that are not shared state modules.
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],

      // Unused code is already caught by tsc; _-prefixed args are the opt-out.
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],

      // The API returns `unknown` payloads that are narrowed deliberately at
      // call sites, so `any` is allowed but must be explicit.
      "@typescript-eslint/no-explicit-any": "off",

      // Empty catch blocks hide real failures. Log or rethrow.
      "no-empty": ["error", { allowEmptyCatch: false }],
    },
  },

  {
    // appState.tsx intentionally exports a provider component and the `useApp`
    // hook from one module. That is the documented React pattern, and Fast
    // Refresh only degrades to a full reload when that file changes.
    files: ["src/lib/appState.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
);
