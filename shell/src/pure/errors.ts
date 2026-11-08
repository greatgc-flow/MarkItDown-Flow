/** Red-phase marker: every pure stub throws this until step 8 goes green. */
export class NotImplementedError extends Error {
  constructor(what: string) {
    super(`Not implemented (red phase): ${what}`);
    this.name = 'NotImplementedError';
  }
}
