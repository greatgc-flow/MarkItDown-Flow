import { App, Modal, Notice, Setting } from 'obsidian';
import type { FileRow, Mode, StrictResult } from '../process/strict';
import type { UiLocale } from '../pure/i18n';

type Actions = {
  retry(): Promise<void>;
  open(row: FileRow): Promise<void>;
  run(row: FileRow, mode: Mode): Promise<void>;
  copy(row: FileRow): Promise<string>;
  photo(row: FileRow, fields: string[]): Promise<{ status: string; fields: Record<string, unknown> }>;
  clipboard(text: string): Promise<void>;
};

export function references(rows: FileRow[], includeLocalPaths = false): string {
  // Spreadsheet readers can interpret leading formula characters even in quoted fields.
  const field = (v: string) => '"' + (/^[=+@\-\t\r]/.test(v) ? "'" : '') + v.replace(/"/g, '""') + '"';
  const headings = ['Input root', 'Source', 'Archive member', 'SHA-256', 'Reason'];
  if (includeLocalPaths) headings.push('Local path');
  const records = rows.map(row => {
    const columns = [String((row.source.root ?? 0) + 1), row.source.originalRelative ?? row.source.relativePath,
      row.source.member ?? '', row.source.sha256, row.reason];
    if (includeLocalPaths) columns.push(row.source.path);
    return columns;
  });
  return [headings, ...records].map(cols => cols.map(field).join(',')).join('\r\n');
}

class PhotoFields extends Modal {
  private selected = new Set(['ImageWidth', 'ImageHeight', 'DateTimeOriginal']);
  constructor(app: App, private row: FileRow, private actions: Actions, private ko: boolean) { super(app); }
  override onOpen(): void {
    this.setTitle(this.ko ? '복사할 사진 정보' : 'Choose photo information to copy');
    const preview = this.contentEl.createDiv();
    let values = '';
    let revision = 0;
    for (const field of ['ImageWidth','ImageHeight','DateTimeOriginal','Make','Model','Artist','SerialNumber','GPSLatitude','GPSLongitude']) {
      new Setting(this.contentEl).setName(field).addToggle(t => t.setValue(this.selected.has(field)).onChange(on => {
        if (on) this.selected.add(field); else this.selected.delete(field);
        revision++;
        values = '';
        preview.empty();
      }));
    }
    new Setting(this.contentEl).addButton(b => b.setButtonText(this.ko ? '선택 정보 미리보기' : 'Preview selected fields').onClick(async () => {
      if (!this.selected.size) return;
      const request = ++revision;
      try {
        const response = await this.actions.photo(this.row, [...this.selected]);
        if (revision !== request) return;
        values = [...this.selected].filter(field => Object.prototype.hasOwnProperty.call(response.fields, field))
          .map(field => field + ': ' + String(response.fields[field])).join('\n');
        preview.empty();
        if (values) preview.createEl('pre', {text: values});
        else preview.createEl('p', {text: response.status === 'no_metadata'
          ? (this.ko ? '이 파일에 선택한 정보가 없습니다.' : 'The selected fields are absent from this file.')
          : (this.ko ? '사진 정보를 읽을 수 없습니다. ' : 'Photo information unavailable. ') + response.status});
      } catch {
        if (revision === request) new Notice(this.ko ? '사진 정보를 읽지 못했습니다.' : 'Could not read photo information.');
      }
    })).addButton(b => b.setButtonText(this.ko ? '표시된 항목 복사' : 'Copy displayed fields').onClick(async () => {
      if (!values) return;
      try {
        await this.actions.clipboard(values);
        new Notice(this.ko ? '사진 정보를 복사했습니다.' : 'Photo information copied.');
        this.close();
      } catch { new Notice(this.ko ? '클립보드에 쓸 수 없습니다.' : 'Clipboard unavailable.'); }
    }));
  }
}

export class StrictResultsModal extends Modal {
  private page = 0;
  private filter = 'all';
  private busy = false;
  private selected = new Set<FileRow>();
  private includeLocalPaths = false;
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
          this.filter=v; this.page=0; this.selected.clear(); this.render();
        });
    });
    const rows = this.result.rows.filter(r => this.filter === 'all' || this.filter === r.outcome || this.filter === r.reason);
    const start = this.page * 25;
    if (this.result.status !== 'complete') new Setting(el).addButton(b => b.setButtonText(this.t('Retry original selection','원래 선택 항목 다시 실행'))
      .onClick(() => this.perform(() => this.actions.retry())));
    const controls = new Setting(el).setName(rows.length ? (start+1) + '–' + Math.min(start+25, rows.length) + ' / ' + rows.length : '0');
    controls.addButton(b => b.setButtonText('‹').setTooltip(this.t('Previous page','이전 페이지')).setDisabled(!this.page).onClick(() => {this.page--;this.render();}));
    controls.addButton(b => b.setButtonText('›').setTooltip(this.t('Next page','다음 페이지')).setDisabled(start+25 >= rows.length).onClick(() => {this.page++;this.render();}));
    const selected = [...this.selected];
    new Setting(el).setName(this.t('Include full local paths in CSV','CSV에 로컬 전체 경로 포함'))
      .addToggle(toggle => toggle.setValue(this.includeLocalPaths).onChange(value => { this.includeLocalPaths = value; }));
    const batch = new Setting(el).setName(this.t('Selected ', '선택 ') + selected.length + ' / ' + rows.length);
    batch.addButton(button => button.setButtonText(this.t('Select all matching','필터 결과 전체 선택'))
      .setDisabled(!rows.length).onClick(() => { this.selected = new Set(rows); this.render(); }));
    batch.addButton(button => button.setButtonText(this.t('Clear selection','선택 해제'))
      .setDisabled(!selected.length).onClick(() => { this.selected.clear(); this.render(); }));
    batch.addButton(button => button.setButtonText(this.t('Copy selected as CSV','선택 목록을 CSV로 복사')).setDisabled(!selected.length)
      .onClick(() => this.perform(() => this.actions.clipboard(references(selected, this.includeLocalPaths)))));
    const originals = selected.filter(row => row.outcome === 'excluded' && row.source.originalSha256);
    batch.addButton(button => button.setButtonText(this.t('Copy originals','원본 사본 만들기') + ' (' + originals.length + ')')
      .setDisabled(!originals.length).onClick(() => this.perform(async () => {
        const counts = new Map<string, number>();
        for (const row of originals) {
          let status: string;
          try { status = await this.actions.copy(row); } catch { status = 'failed'; }
          counts.set(status, (counts.get(status) ?? 0) + 1);
        }
        return [...counts].map(([status,n]) => status + ' ' + n).join(' · ');
      })));
    for (const row of rows.slice(start,start+25)) {
      const item = new Setting(el).setName(row.source.relativePath).setDesc([label[row.outcome] ?? row.outcome,
        label[row.reason] ?? row.reason, row.action].filter(Boolean).join(' · '));
      item.addToggle(toggle => toggle.setValue(this.selected.has(row)).onChange(checked => {
        if (checked) this.selected.add(row); else this.selected.delete(row);
        this.render();
      }));
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
