import obsidianmd from 'eslint-plugin-obsidianmd';
import tseslint from 'typescript-eslint';

export default [{
  files: ['shell/src/**/*.ts'],
  languageOptions: { parser: tseslint.parser },
  plugins: { obsidianmd },
  // Enforce the rule that blocked directory review. Adopt other rules separately.
  rules: { 'obsidianmd/no-static-styles-assignment': 'error' },
}];
