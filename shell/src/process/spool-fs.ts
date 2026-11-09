/**
 * SpoolFs over the owned `<plugin-dir>/spool` directory (20_SHELL.md REQ-SHL-13).
 * Reads are ranged (`FileSystemOps.readRange`), so draining an N-byte report
 * costs N bytes of I/O in 64 KiB windows, never a whole-file read per window
 * (M3 N-10).
 */
import { joinPath } from '../pure/paths';
import type { SpoolFs } from '../pure/spool';
import type { FileSystemOps, HostPlatform } from './types';

export class DirectorySpoolFs implements SpoolFs {
  constructor(
    private readonly fs: FileSystemOps,
    private readonly dir: string,
    private readonly platform: HostPlatform,
  ) {}

  private at(name: string): string {
    return joinPath(this.platform, this.dir, name);
  }

  async append(name: string, chunk: Uint8Array): Promise<void> {
    await this.fs.mkdir(this.dir);
    await this.fs.appendFile(this.at(name), chunk);
  }

  async read(name: string, offset: number, max: number): Promise<Uint8Array> {
    return this.fs.readRange(this.at(name), offset, max);
  }

  async remove(name: string): Promise<void> {
    await this.fs.remove(this.at(name));
  }

  async list(): Promise<string[]> {
    return this.fs.list(this.dir);
  }
}
