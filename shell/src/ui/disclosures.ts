import { formatMessage, type UiLocale } from '../pure/i18n';

export function addDisclosureLink(parent: HTMLElement, locale: UiLocale): void {
  parent.createEl('a', {
    text: formatMessage(locale, 'shell.disclosures.link'),
    attr: {
      href: 'https://github.com/greatgc-flow/MarkItDown-Flow/blob/2.1.0/README.md#network-services-and-purpose',
      target: '_blank',
      rel: 'noopener noreferrer',
    },
  });
}
