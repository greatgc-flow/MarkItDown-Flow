const path = require('node:path');

/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/test'],
  testMatch: ['**/test/**/*.test.ts'],
  // Titles are `JT-nn REQ-SHL-xx ...: description` (shell/test/req.ts); trace.py parses them.
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: path.join(__dirname, '..', 'build', 'trace'),
        outputName: 'junit-shell.xml',
        suiteName: 'shell',
        classNameTemplate: '{filepath}',
        titleTemplate: '{title}',
        ancestorSeparator: ' > ',
        addFileAttribute: 'true',
      },
    ],
  ],
  // Red/green discipline: a skipped or focused test is a failure, never evidence.
  errorOnDeprecated: true,
  testTimeout: 10000,
  // No watchers, no network, no coverage thresholds yet (step 8 is pure).
  collectCoverage: false,
};
