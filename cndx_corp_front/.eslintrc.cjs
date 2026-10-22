/**
 * This is intended to be a basic starting point for linting in your app.
 * It relies on recommended configs out of the box for simplicity, but you can
 * and should modify this configuration to best suit your team's needs.
 */

/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
  env: {
    browser: true,
    commonjs: true,
    es6: true,
  },
  ignorePatterns: ["!**/.server", "!**/.client"],

  // Base config
  extends: ["eslint:recommended"],

  overrides: [
    // React
    {
      files: ["**/*.{js,jsx,ts,tsx}"],
      plugins: ["react", "jsx-a11y", "eslint-comments", "unused-imports"],
      extends: [
        "plugin:react/recommended",
        "plugin:react/jsx-runtime",
        "plugin:react-hooks/recommended",
        "plugin:jsx-a11y/recommended",
      ],
      settings: {
        react: {
          version: "detect",
        },
        formComponents: ["Form"],
        linkComponents: [
          { name: "Link", linkAttribute: "to" },
          { name: "NavLink", linkAttribute: "to" },
        ],
        "import/resolver": {
          typescript: {},
        },
      },
      rules: {
        // FE-005 Reactコンポーネント名
        'react/jsx-pascal-case': 'error',

        // FE-008 PropTypes禁止
        'no-restricted-imports': [
          'error',
          {
            paths: [
              {
                name: 'prop-types',
                message: 'TypeScriptの型を使用する',
              },
            ],
          },
        ],

        // FE-013 / COM-016 eslint-disable管理
        '@eslint-community/eslint-comments/require-description': 'error',

        // FE-015 三項演算子ネスト禁止
        'no-nested-ternary': 'error',

        // FE-017 / COM-010 未使用import・未使用変数 (JSファイル用)
        'no-unused-vars': 'off',
        'unused-imports/no-unused-imports': 'error',
        'unused-imports/no-unused-vars': [
          'error',
          {
            vars: 'all',
            varsIgnorePattern: '^_',
            args: 'after-used',
            argsIgnorePattern: '^_',
          },
        ],

        // FE-019 自己閉じタグ
        'react/self-closing-comp': [
          'error',
          {
            component: true,
            html: true,
          },
        ],
      }
    },

    // Typescript
    {
      files: ["**/*.{ts,tsx}"],
      plugins: ["@typescript-eslint", "import", "unused-imports"],
      parser: "@typescript-eslint/parser",
      settings: {
        "import/internal-regex": "^~/",
        "import/resolver": {
          node: {
            extensions: [".ts", ".tsx"],
          },
          typescript: {
            alwaysTryTypes: true,
          },
        },
      },
      extends: [
        "plugin:@typescript-eslint/recommended",
        "plugin:import/recommended",
        "plugin:import/typescript",
      ],
      rules: {
        "react/prop-types": "off", // TypeScript なら不要なので無効化
        // FE-001 変数・関数名
        '@typescript-eslint/naming-convention': [
          'error',
          {
            selector: 'variableLike',
            format: ['camelCase'],
          },
          {
            selector: 'typeLike',
            format: ['PascalCase'],
          },
        ],

        // FE-009 any禁止
        '@typescript-eslint/no-explicit-any': 'error',

        // FE-010 不要な型アサーション禁止
        '@typescript-eslint/no-unnecessary-type-assertion': 'error',

        // FE-017 / COM-010 未使用import・未使用変数 (TSファイル用)
        '@typescript-eslint/no-unused-vars': 'off',
        'unused-imports/no-unused-imports': 'error',
        'unused-imports/no-unused-vars': [
          'error',
          {
            vars: 'all',
            varsIgnorePattern: '^_',
            args: 'after-used',
            argsIgnorePattern: '^_',
          },
        ],
      }
    },

    // Node
    {
      files: [".eslintrc.cjs"],
      env: {
        node: true,
      },
    },
  ],
};
