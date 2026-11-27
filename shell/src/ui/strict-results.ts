import { App, Modal, Notice, Setting } from 'obsidian';
import type { FileRow, Mode, StrictResult } from '../process/strict';
import type { UiLocale } from '../pure/i18n';

type Actions = {
  open(row: FileRow): Promise<void>;
  run(row: FileRow, mode: Mode): Promise<void>;
  copy(row: FileRow): Promise<string>;
  photo(row: FileRow, fields: string[]): Promise<string>;
  clipboard(text: string): Promise<void>;
};

export function references(rows: FileRow[]): string {
  // Spreadsheet readers can interpret leading formula characters even in quoted fields.
  const field = (v: string) => '"' + (/^[=+@\-\t\r]/.test(v) ? "'" : '') + v.replace(/"/g, '""') + '"';
  return [['Source', 'Archive member', 'SHA-256', 'Reason'], ...rows.map(r =>
    [r.source.path, r.source.member ?? '', r.source.sha256, r.reason])].map(cols => cols.map(field).join(',')).join('\r\n');
}

class PhotoFields extends Modal {
  private selected = new Set(['ImageWidth', 'ImageHeight', 'DateTimeOriginal']);
  constructor(app: App, private row: FileRow, private actions: Actions, private ko: boolean) { super(app); }
  override onOpen(): void {
    this.setTitle(this.ko ? '복사할 사진 정보' : 'Choose photo information to copy');
    for (const field of ['ImageWidth','ImageHeight','DateTimeOriginal','Make','Model','Artist','SerialNumber','GPSLatitude','GPSLongitude']) {
      new Setting(this.contentEl).setName(field).addToggle(t => t.setValue(this.selected.has(field)).onChange(on => {
        if (on) this.selected.add(field); else this.selected.delete(field);
      }));
    }
    new Setting(this.contentEl).addButton(b => b.setButtonText(this.ko ? '선택 항목 복사' : 'Copy selected fields').onClick(async () => {
      if (this.selected.size) new Notice(await this.actions.photo(this.row, [...this.selected]));
      this.close();
    }));
  }
}

export class StrictResultsModal extends Modal {
  private page = 0;
  private filter = 'all';
  private busy = false;
  constructor(app: App, private result: StrictResult, private locale: UiLocale, private actions: Actions) { super(app); }
  private t(en: string, ko: string): string { return this.locale === 'ko' ? ko : en; }
  override onOpen(): void { this.render(); }
  private async perform(action: () => Promise<unknown>): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    try { const message = await action(); if (typeof message === 'string') new Notice(message); }
    catch { new Notice(this.t('Action failed. Check the source and output directory.', '작업에 실패했습니다. 원본과 출력 폴더를 확인하세요.')); }
    finally { this.busy = false; }
  }
  private render(): void {
    const el = this.contentEl;
    el.empty();
    this.setTitle(this.t('Document results', '문서 처리 결과'));
    const label: Record<string, string> = {
      complete:this.t('Complete','완료'), excluded:this.t('Excluded','제외'), eligible:this.t('Eligible','변환 가능'),
      failed:this.t('Failed','실패'), ocr_required:this.t('External OCR needed','외부 OCR 필요'),
      undetermined:this.t('Needs inspection','확인 필요'), interrupted:this.t('Interrupted','중단'),
      direct:this.t('Direct text','텍스트'), empty:this.t('Empty','빈 문서'),
    };
    const counts = new Map<string, number>();
    for (const r of this.result.rows) counts.set(r.outcome, (counts.get(r.outcome) ?? 0) + 1);
    el.createEl('p', {text: [label[this.result.status] ?? this.result.status,
      ...[...counts].map(([k,n]) => (label[k] ?? k) + ' ' + n), this.t('Skipped ', '건너뜀 ') + this.result.skipped].join(' · ')});
    new Setting(el).setName(this.t('Show','표시')).addDropdown(d => {
      d.addOptions({all:this.t('All','전체'), ocr_required:label.ocr_required, excluded:label.excluded,
        undetermined:label.undetermined, failed:label.failed, complete:label.complete}).setValue(this.filter).onChange(v => {
          this.filter=v; this.page=0; this.render();
        });
    });
    const rows = this.result.rows.filter(r => this.filter === 'all' || this.filter === r.outcome || this.filter === r.reason);
    const start = this.page * 25;
    const controls = new Setting(el).setName(rows.length ? (start+1) + '–' + Math.min(start+25, rows.length) + ' / ' + rows.length : '0');
    controls.addButton(b => b.setButtonText('‹').setTooltip(this.t('Previous page','이전 페이지')).setDisabled(!this.page).onClick(() => {this.page--;this.render();}));
    controls.addButton(b => b.setButtonText('›').setTooltip(this.t('Next page','다음 페이지')).setDisabled(start+25 >= rows.length).onClick(() => {this.page++;this.render();}));
    controls.addButton(b => b.setButtonText(this.t('Copy list as CSV','목록을 CSV로 복사')).setDisabled(!rows.length)
      .onClick(() => this.perform(() => this.actions.clipboard(references(rows)))));
    for (const row of rows.slice(start,start+25)) {
      const item = new Setting(el).setName(row.source.relativePath).setDesc([label[row.outcome] ?? row.outcome,
        label[row.reason] ?? row.reason, row.action].filter(Boolean).join(' · '));
      item.addButton(b => b.setButtonText(this.t('Show original','원본 위치')).onClick(() => this.perform(() => this.actions.open(row))));
      if (row.source.format === 'pdf') {
        item.addButton(b => b.setButtonText(this.t('Inspect','구성 분석')).onClick(() => this.perform(() => this.actions.run(row,'preview'))));
        if (row.reason === 'ocr_required') item.addButton(b => b.setButtonText(this.t('Extract existing text','텍스트만 추출')).onClick(() => this.perform(() => this.actions.run(row,'extract-text'))));
      }
      if (row.outcome === 'excluded' && row.source.originalSha256) {
        item.addButton(b => b.setButtonText(this.t('Copy original','원본 사본 만들기')).onClick(() => this.perform(() => this.actions.copy(row))));
      }
      if (row.source.format === 'jpeg' || row.source.format === 'png') {
        item.addButton(b => b.setButtonText(this.t('Photo information','사진 정보')).onClick(() =>
          new PhotoFields(this.app,row,this.actions,this.locale === 'ko').open()));
      }
      const f = row.inspection;
      if (f?.pages) {
        const roles: Record<string, number> = {};
        for (const p of f.pages) roles[p.role] = (roles[p.role] ?? 0) + 1;
        el.createEl('p',{text:this.t('Pages inspected ','검사한 페이지 ') + f.inspected_pages + '/' + f.total_pages + ' · ' +
          Object.entries(roles).map(([k,v]) => k + ' ' + v).join(' · ')});
        el.createEl('p',{text:this.t('Measured area ','면적을 측정한 페이지 ') + f.measured_pages + '/' + f.total_pages + ' · ' +
          (f.area_percent ? Object.entries(f.area_percent).map(([k,v]) => k + ' ≈' + v + '%').join(' · ') : this.t('Unavailable','측정 불가'))});
      }
    }
  }
}
