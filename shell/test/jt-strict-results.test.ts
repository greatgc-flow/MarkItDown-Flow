import { beginJournal, lastJob } from '../src/process/node-apis';
import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { req } from './req';
import { StrictStream, type FileRow } from '../src/process/strict';
import { references } from '../src/ui/strict-results';
const R = req('REQ-SHL-11');
const item: FileRow = {kind:'file', outcome:'excluded', reason:'ocr_required',
  source:{path:'/sensitive/home/Archive.zip', relativePath:'Archive.zip/메모,1.pdf',
    originalRelative:'Archive.zip', member:'메모,1.pdf', sha256:'a'.repeat(64)}};
it(R('JT-11 CSV exposes machine-local paths only on explicit selection'), () => {
  expect(references([item])).not.toContain('/sensitive/home');
  expect(references([item])).toContain('"메모,1.pdf"');
  expect(references([item], true)).toContain('"/sensitive/home/Archive.zip"');
});
it(R('JT-11 an incomplete stream and a mismatched footer cannot report a completed job'), () => {
  const stream = new StrictStream('run');
  const header = {schema:2, policy:'strict-v1', mode:'run', run_id:'example'};
  stream.accept(JSON.stringify({...header,kind:'header'}));
  stream.accept(JSON.stringify(item));
  expect(stream.finish(0).status).toBe('interrupted');
  expect(() => stream.accept(JSON.stringify({...header,kind:'footer',files:0,exit:0,counts:{}}))).toThrow();
  stream.accept(JSON.stringify({...header,kind:'footer',files:1,exit:0,counts:{excluded:1}}));
  expect(stream.finish(0).status).toBe('complete');
});

it(R('JT-11 completed history is bounded and reopening an interrupted job preserves completed rows'), async () => {
  const home = await fs.mkdtemp(path.join(os.tmpdir(), 'mdflow-history-test-'));
  const source = path.join(home, 'sample.pdf');
  const result = {rows:[item], status:'complete' as const, skipped:0};
  try {
    for (let i=0; i<12; i++) {
      const job = beginJournal(home, home, [source], 'run', home);
      job.append(item);
      job.close(result);
    }
    const root = path.join(home, '.mdflow', 'jobs');
    const folder = path.join(root,(await fs.readdir(root))[0]);
    expect((await fs.readdir(folder)).length).toBeLessThanOrEqual(8);
    const job = beginJournal(home, home, [source], 'run', home);
    job.append(item);
    job.close();
    const recovered = await lastJob(home, home);
    expect(recovered?.result.status).toBe('interrupted');
    expect(recovered?.result.rows).toHaveLength(1);
  } finally { await fs.rm(home, {force:true,recursive:true}); }
});
