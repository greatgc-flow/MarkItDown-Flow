import { access, mkdtemp, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { DataAdapter } from 'obsidian';
import { VaultDataStore } from '../src/ui/data-store';
import { req } from './req';
const R = req('REQ-SHL-05');
let root: string;
beforeEach(async () => { root = await mkdtemp(join(tmpdir(), 'mdflow-store-')); });
afterEach(async () => { await rm(root, { recursive: true, force: true }); });
function adapter(options: { failRename?: boolean; partialWrite?: boolean; failCleanup?: boolean } = {}): DataAdapter {
  return {
    async exists(path: string) { try { await access(path); return true; } catch { return false; } },
    async write(path: string, text: string) {
      await writeFile(path, options.partialWrite ? text.slice(0, 3) : text);
      if (options.partialWrite) throw new Error('write failed');
    },
    async rename(from: string, to: string) {
      if (options.failRename) throw new Error('rename failed');
      await rename(from, to);
    },
    async remove(path: string) {
      if (options.failCleanup) throw new Error('cleanup failed');
      await rm(path);
    },
  } as unknown as DataAdapter;
}
it(R('JT-05 adapter replaces existing settings without deleting the target first'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  const a = adapter();
  const remove = jest.spyOn(a, 'remove');
  await new VaultDataStore(a, root).write('data.json', '{"new":true}');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"new":true}');
  expect(remove).not.toHaveBeenCalled();
  expect(await readdir(root)).toEqual(['data.json']);
});
it(R('JT-05 adapter rename failure preserves exact original bytes and cleans staging'), async () => {
  const original = '{"enginePython":"/old/python","history":[1]}';
  await writeFile(join(root, 'data.json'), original);
  await expect(new VaultDataStore(adapter({ failRename: true }), root).write('data.json', '{}')).rejects.toThrow('rename failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe(original);
  expect(await readdir(root)).toEqual(['data.json']);
});
it(R('JT-05 adapter partial staging failure removes partial JSON and preserves original'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  await expect(new VaultDataStore(adapter({ partialWrite: true }), root).write('data.json', '{"new":true}')).rejects.toThrow('write failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"old":true}');
  expect(await readdir(root)).toEqual(['data.json']);
});
it(R('JT-05 adapter cleanup failure preserves original and the save error'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  await expect(new VaultDataStore(adapter({ failRename: true, failCleanup: true }), root).write('data.json', '{}')).rejects.toThrow('rename failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"old":true}');
});
it(R('JT-05 adapter serializes overlapping saves and recovers after rejection'), async () => {
  const a = adapter();
  const realRename = a.rename.bind(a);
  let calls = 0;
  jest.spyOn(a, 'rename').mockImplementation(async (from, to) => {
    if (++calls === 1) throw new Error('first save failed');
    await realRename(from, to);
  });
  const store = new VaultDataStore(a, root);
  const results = await Promise.allSettled([store.write('data.json', '{"n":1}'), store.write('data.json', '{"n":2}'), store.write('data.json', '{"n":3}')]);
  expect(results.map(r => r.status)).toEqual(['rejected', 'fulfilled', 'fulfilled']);
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"n":3}');
  expect(await readdir(root)).toEqual(['data.json']);
});
