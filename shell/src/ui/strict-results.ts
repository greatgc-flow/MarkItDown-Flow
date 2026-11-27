import { App, Modal, Notice, Setting } from 'obsidian';
import type { FileRow, Mode, StrictResult } from '../process/strict';
import type { UiLocale } from '../pure/i18n';

const resultLabels: Record<string, [string, string]> = {
  complete:['Complete','완료'], excluded:['Excluded','제외'], eligible:['Eligible','변환 가능'],
  failed:['Failed','실패'], interrupted:['Interrupted','중단'], empty:['Empty','빈 문서'],
  direct:['Direct text','직접 추출 가능'], ocr_required:['External OCR needed','외부 OCR 필요'],
  undetermined:['Needs inspection','확인 필요'], protected:['Password or access protection','암호 또는 접근 제한'],
  unsupported:['Unsupported format','지원하지 않는 형식'], legacy:['Legacy format','구형 형식'],
  limit:['Inspection limit reached','검사 한도 도달'], limited:['Incomplete coverage','일부만 검사됨'],
  corrupt:['Damaged file','손상된 파일'], read_failed:['Could not read the source','원본 읽기 실패'],
  write_failed:['Could not write the output','결과 저장 실패'], source_changed:['Source changed','원본 변경됨'],
  edited_output:['Output path conflict','출력 경로 충돌'],
  conversion_failed:['Conversion failed','변환 실패'], saved:['Saved','저장됨'], reused:['Already saved','기존 결과 재사용'],
  no_usable_text:['No existing text to extract','추출할 텍스트 없음'], unavailable:['Unavailable','사용할 수 없음'],
  use_standard_conversion:['Use normal conversion','일반 변환 가능'], not_found:['ExifTool not installed','ExifTool 미설치'],
  too_old:['Update ExifTool','ExifTool 업데이트 필요'], unusable:['ExifTool could not read this image','ExifTool로 이미지를 읽을 수 없음'],
  text:['Text','텍스트'], image:['Image','이미지'], mixed:['Text and scan','텍스트와 스캔'],
  blank:['Blank','빈 공간'], other:['Other','기타'], ocr:['Scanned','스캔'],
};
function describe(value: string, locale: UiLocale): string {
  return resultLabels[value]?.[locale === 'ko' ? 1 : 0] ?? value;
}

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

const photoFieldNames: Record<string, [string, string]> = {
  ImageWidth:['Image width','사진 너비'], ImageHeight:['Image height','사진 높이'],
  DateTimeOriginal:['Date taken','촬영 일시'], Make:['Device maker','기기 제조사'],
  Model:['Device model','기기 모델'], Artist:['Author','작성자'], SerialNumber:['Device serial number','기기 일련번호'],
  GPSLatitude:['GPS latitude','GPS 위도'], GPSLongitude:['GPS longitude','GPS 경도'],
};

class PhotoFields extends Modal {
  private selected = new Set(['ImageWidth', 'ImageHeight', 'DateTimeOriginal']);
  constructor(app: App, private row: FileRow, private actions: Actions, private ko: boolean) { super(app); }
  override onOpen(): void {
    this.setTitle(this.ko ? '복사할 사진 정보' : 'Choose photo information to copy');
    const preview = this.contentEl.createDiv();
    let values = '';
    let revision = 0;
    for (const [field,names] of Object.entries(photoFieldNames)) {
      new Setting(this.contentEl).setName(names[this.ko ? 1 : 0]).addToggle(t => t.setValue(this.selected.has(field)).onChange(on => {
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
          : (this.ko ? '사진 정보를 읽을 수 없습니다. ' : 'Photo information unavailable. ') + describe(response.status,this.ko ? 'ko' : 'en')});
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
    try { const message = await action(); if (typeof message === 'string') new Notice(describe(message, this.locale)); }
    catch { new Notice(this.t('Action failed. Check the source and output directory.', '작업에 실패했습니다. 원본과 출력 폴더를 확인하세요.')); }
    finally { this.busy = false; }
  }
  private render(): void {
    const el = this.contentEl;
    el.empty();
    this.setTitle(this.t('Document results', '문서 처리 결과'));
    const label = (value: string) => describe(value, this.locale);
    const counts = new Map<string, number>();
    for (const r of this.result.rows) counts.set(r.outcome, (counts.get(r.outcome) ?? 0) + 1);
    el.createEl('p', {text: [label(this.result.status),
      ...[...counts].map(([k,n]) => label(k) + ' ' + n), this.t('Skipped ', '건너뜀 ') + this.result.skipped].join(' · ')});
    new Setting(el).setName(this.t('Show','표시')).addDropdown(d => {
      d.addOptions({all:this.t('All','전체'), ocr_required:label('ocr_required'), excluded:label('excluded'),
        undetermined:label('undetermined'), failed:label('failed'), complete:label('complete')}).setValue(this.filter).onChange(v => {
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
        return [...counts].map(([status,n]) => label(status) + ' ' + n).join(' · ');
      })));
    for (const row of rows.slice(start,start+25)) {
      const item = new Setting(el).setName(row.source.relativePath).setDesc([label(row.outcome),
        label(row.reason), row.action && label(row.action)].filter(Boolean).join(' · '));
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
          Object.entries(roles).map(([k,v]) => label(k) + ' ' + v).join(' · ')});
        el.createEl('p',{text:this.t('Measured area ','면적을 측정한 페이지 ') + f.measured_pages + '/' + f.total_pages + ' · ' +
          (f.area_percent ? Object.entries(f.area_percent).map(([k,v]) => label(k) + ' ≈' + v + '%').join(' · ') : this.t('Unavailable','측정 불가'))});
      }
    }
  }
}
