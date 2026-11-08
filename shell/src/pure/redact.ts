/**
 * Shell-side redaction for notices, logs and diagnostics
 * (20_SHELL.md REQ-SHL-05/06/18; SPEC section 9 REQ-SEC-02).
 */

export interface RedactOptions {
  /** Known credential values; every occurrence becomes `***`. */
  secrets?: readonly string[];
  /** Home directory prefix; replaced by `~`. */
  home?: string;
  /** Vault root; paths under it become vault-relative. */
  vault?: string;
}

export const REDACTED = '***';

function replaceAll(text: string, needle: string, replacement: string): string {
  return needle.length === 0 ? text : text.split(needle).join(replacement);
}

/** Both separator spellings of a path prefix, longest first. */
function prefixVariants(prefix: string): string[] {
  const trimmed = prefix.replace(/[\\/]+$/, '');
  if (!trimmed) return [];
  const variants = new Set<string>([trimmed, trimmed.replace(/\\/g, '/'), trimmed.replace(/\//g, '\\')]);
  return [...variants].sort((a, b) => b.length - a.length);
}

export function redactText(text: string, options: RedactOptions): string {
  let out = text;
  const secrets = [...(options.secrets ?? [])].filter((s) => s.length > 0).sort((a, b) => b.length - a.length);
  for (const secret of secrets) out = replaceAll(out, secret, REDACTED);
  if (options.vault) {
    for (const variant of prefixVariants(options.vault)) {
      out = replaceAll(out, variant + '/', '');
      out = replaceAll(out, variant + '\\', '');
    }
  }
  if (options.home) {
    for (const variant of prefixVariants(options.home)) out = replaceAll(out, variant, '~');
  }
  return out;
}

/** Deep-redact every string in a JSON-like value. */
export function redactValue<T>(value: T, options: RedactOptions): T {
  const walk = (v: unknown): unknown => {
    if (typeof v === 'string') return redactText(v, options);
    if (Array.isArray(v)) return v.map(walk);
    if (v !== null && typeof v === 'object') {
      const out: Record<string, unknown> = {};
      for (const [k, inner] of Object.entries(v as Record<string, unknown>)) out[k] = walk(inner);
      return out;
    }
    return v;
  };
  return walk(value) as T;
}
