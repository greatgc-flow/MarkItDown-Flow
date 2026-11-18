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
const exists = async (path: string) => { try { await access(path); return true; } catch { return false; } };
type Options = { failRename?: boolean; failRenameOntoTarget?: boolean; failRestore?: boolean; partialWrite?: boolean; failCleanup?: boolean; failWriteBackup?: boolean };
/** Real-filesystem bridge with Obsidian's adapter semantics: rename refuses an existing destination
 * (FileSystemAdapter.rename in Obsidian 1.15.1 throws "Destination file already exists!"). */
function adapter(options: Options = {}): DataAdapter {
  return {
    exists,
    async read(path: string) { return readFile(path, 'utf8'); },
    async write(path: string, text: string) {
      if (options.failWriteBackup && path.endsWith('.bak')) throw new Error('backup write failed');
      await writeFile(path, options.partialWrite ? text.slice(0, 3) : text);
      if (options.partialWrite) throw new Error('write failed');
    },
    async rename(from: string, to: string) {
      if (options.failRename) throw new Error('rename failed');
      if (options.failRenameOntoTarget && to.endsWith('data.json') && from.includes('.tmp-')) throw new Error('swap failed');
      if (options.failRestore && from.endsWith('.bak')) throw new Error('restore failed');
      if (await exists(to)) throw new Error('Destination file already exists!');
      await rename(from, to);
    },
    async remove(path: string) {
      if (options.failCleanup) throw new Error('cleanup failed');
      await rm(path);
    },
  } as unknown as DataAdapter;
}
it(R('JT-05 adapter replaces existing settings under Obsidian rename semantics and never removes the original first'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  const a = adapter();
  const remove = jest.spyOn(a, 'remove');
  await new VaultDataStore(a, root).write('data.json', '{"new":true}');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"new":true}');
  expect(remove.mock.calls.map(([path]) => path.split(/[\\/]/).pop())).toEqual(['data.json.bak']);
  expect(await readdir(root)).toEqual(['data.json']);
});
it(R('JT-05 adapter rename failure preserves exact original bytes and cleans staging'), async () => {
  const original = '{"enginePython":"/old/python","history":[1]}';
  await writeFile(join(root, 'data.json'), original);
  await expect(new VaultDataStore(adapter({ failRename: true }), root).write('data.json', '{}')).rejects.toThrow('rename failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe(original);
  expect(await readdir(root)).toEqual(['data.json']);
});
it(R('JT-05 adapter swap failure restores the original from the backup'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  await expect(new VaultDataStore(adapter({ failRenameOntoTarget: true }), root).write('data.json', '{"new":true}')).rejects.toThrow('swap failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"old":true}');
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
it(R('JT-05 adapter recovers an interrupted swap and a stale backup on the next save'), async () => {
  // Interrupted after the original moved aside: only the backup holds valid (old) JSON.
  await writeFile(join(root, 'data.json.bak'), '{"old":true}');
  const store = new VaultDataStore(adapter(), root);
  expect(await store.read('data.json')).toBe('{"old":true}');
  await store.write('data.json', '{"new":true}');
  expect(await store.read('data.json')).toBe('{"new":true}');
  expect(await readdir(root)).toEqual(['data.json']);
  // A save whose backup cannot be removed neutralizes it (no raw settings remain); the next save removes it.
  await writeFile(join(root, 'data.json'), '{"raw":"v1-secret"}');
  await new VaultDataStore(adapter({ failCleanup: true }), root).write('data.json', '{"n":1}');
  expect((await readdir(root)).sort()).toEqual(['data.json', 'data.json.bak']);
  expect(await readFile(join(root, 'data.json.bak'), 'utf8')).toBe('{"n":1}');
  await new VaultDataStore(adapter(), root).write('data.json', '{"n":2}');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"n":2}');
  expect(await readdir(root)).toEqual(['data.json']);
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
it(R('JT-05 adapter reports a save whose raw backup can be neither removed nor neutralized'), async () => {
  await writeFile(join(root, 'data.json'), '{"raw":"v1-secret"}');
  await expect(new VaultDataStore(adapter({ failCleanup: true, failWriteBackup: true }), root).write('data.json', '{"n":1}')).rejects.toThrow('backup write failed');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"n":1}');
});
it(R('JT-05 adapter keeps the original readable when both the swap and its rollback fail'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  const store = new VaultDataStore(adapter({ failRenameOntoTarget: true, failRestore: true }), root);
  await expect(store.write('data.json', '{"new":true}')).rejects.toThrow('swap failed');
  expect(await readdir(root)).toEqual(['data.json.bak']);
  expect(await store.read('data.json')).toBe('{"old":true}');
  expect(await store.list()).toEqual(['data.json']);
  // A failed save over a backup-only state leaves that backup readable too.
  await expect(new VaultDataStore(adapter({ failRename: true }), root).write('data.json', '{"newer":true}')).rejects.toThrow('rename failed');
  expect(await new VaultDataStore(adapter(), root).read('data.json')).toBe('{"old":true}');
});
it(R('JT-05 adapter serializes reads with an in-flight save'), async () => {
  await writeFile(join(root, 'data.json'), '{"old":true}');
  const store = new VaultDataStore(adapter(), root);
  const saving = store.write('data.json', '{"new":true}');
  const [read, listed] = await Promise.all([store.read('data.json'), store.list(), saving]);
  expect(read).toBe('{"new":true}');
  expect(listed).toEqual(['data.json']);
});
it(R('JT-05 adapter discards a raw backup left beside an installed target when settings are read at startup'), async () => {
  // Interrupted after the new target was installed but before its backup was removed.
  await writeFile(join(root, 'data.json'), '{"schema":2}');
  await writeFile(join(root, 'data.json.bak'), '{"raw":"v1-secret"}');
  expect(await new VaultDataStore(adapter(), root).read('data.json')).toBe('{"schema":2}');
  expect(await readdir(root)).toEqual(['data.json']);
  // Removal denied: the read rejects and nothing is copied over the backup (the target is unvalidated).
  await writeFile(join(root, 'data.json'), '{"raw":"v1-target"}');
  await writeFile(join(root, 'data.json.bak'), '{"raw":"v1-secret"}');
  await expect(new VaultDataStore(adapter({ failCleanup: true }), root).read('data.json')).rejects.toThrow('cleanup failed');
  expect(await readFile(join(root, 'data.json.bak'), 'utf8')).toBe('{"raw":"v1-secret"}');
  expect(await readFile(join(root, 'data.json'), 'utf8')).toBe('{"raw":"v1-target"}');
});
