import nextConfig from 'eslint-config-next';
import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypescript from 'eslint-config-next/typescript';
import pluginSecurity from 'eslint-plugin-security';

const eslintConfig = [
  {
    ignores: [
      '.claude/**',
      'scripts/**',
      '.quality/**',
      'docs/**',
      'node_modules/**',
      '**/*.generated.ts',
    ],
  },
  ...nextConfig,
  ...nextCoreWebVitals,
  ...nextTypescript,
  pluginSecurity.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      /** セキュリティ: 危険なパターンをエラーに昇格 */
      'security/detect-eval-with-expression': 'error',
      'security/detect-non-literal-fs-filename': 'off',
      'security/detect-object-injection': 'off',
    },
  },
];

export default eslintConfig;
