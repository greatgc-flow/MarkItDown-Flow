/**
 * Minimal in-process stand-in for the public `obsidian` API (own work, written
 * from the public type declarations only; no Obsidian or v1 code).
 *
 * Jest resolves `import ... from 'obsidian'` to this file (manual mock under
 * `roots`). Tests import `mockState` from here to observe notices, modals,
 * network attempts, registered events and the in-memory vault adapter.
 *
 * There is no DOM in the `node` test environment. `FakeElement` implements the
 * subset of the Obsidian-augmented HTMLElement surface the shell may use
 * (`createEl`, `createDiv`, `createSpan`, `setText`, `empty`, `addClass`, ...).
 * Assigning `innerHTML` throws: shell UI must render text nodes only.
 */

import type { App as ObsidianApp, Plugin as ObsidianPlugin, PluginManifest as ObsidianManifest } from 'obsidian';

type Listener = (event: FakeEvent) => unknown;

export interface FakeEvent {
  type: string;
  defaultPrevented?: boolean;
  preventDefault?: () => void;
  stopPropagation?: () => void;
  dataTransfer?: { files?: { path?: string; name: string }[]; types?: string[]; getData?: (t: string) => string };
  [key: string]: unknown;
}

export interface DomElementInfoLike {
  text?: string;
  cls?: string | string[];
  attr?: Record<string, string | number | boolean | null>;
  title?: string;
  placeholder?: string;
  type?: string;
  value?: string;
  href?: string;
}

export class FakeElement {
  readonly children: FakeElement[] = [];
  parent: FakeElement | null = null;
  readonly classes = new Set<string>();
  readonly attributes = new Map<string, string>();
  readonly listeners = new Map<string, Listener[]>();
  style: Record<string, string> = {};
  disabled = false;
  value = '';
  checked = false;
  private ownText = '';

  constructor(readonly tagName: string = 'div') {}

  get textContent(): string {
    return this.ownText + this.children.map((c) => c.textContent).join('');
  }

  set textContent(value: string) {
    this.ownText = value;
    this.children.length = 0;
  }

  get innerHTML(): string {
    return this.textContent;
  }

  set innerHTML(_value: string) {
    throw new Error('innerHTML is forbidden in the shell: render literal text nodes (REQ-SHL-14)');
  }

  get outerHTML(): string {
    throw new Error('outerHTML is not available in the fake DOM');
  }

  setText(value: string | { textContent?: string | null }): void {
    this.textContent = typeof value === 'string' ? value : (value.textContent ?? '');
  }

  empty(): void {
    this.ownText = '';
    for (const child of this.children) child.parent = null;
    this.children.length = 0;
  }

  detach(): void {
    if (!this.parent) return;
    const idx = this.parent.children.indexOf(this);
    if (idx >= 0) this.parent.children.splice(idx, 1);
    this.parent = null;
  }

  remove(): void {
    this.detach();
  }

  addClass(...classes: string[]): void {
    for (const c of classes) for (const part of c.split(/\s+/)) if (part) this.classes.add(part);
  }

  removeClass(...classes: string[]): void {
    for (const c of classes) this.classes.delete(c);
  }

  toggleClass(classes: string | string[], value: boolean): void {
    for (const c of Array.isArray(classes) ? classes : [classes]) {
      if (value) this.classes.add(c);
      else this.classes.delete(c);
    }
  }

  hasClass(cls: string): boolean {
    return this.classes.has(cls);
  }

  get className(): string {
    return [...this.classes].join(' ');
  }

  get classList(): { add: (...c: string[]) => void; remove: (...c: string[]) => void; contains: (c: string) => boolean } {
    return {
      add: (...c: string[]) => this.addClass(...c),
      remove: (...c: string[]) => this.removeClass(...c),
      contains: (c: string) => this.hasClass(c),
    };
  }

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, String(value));
  }

  getAttribute(name: string): string | null {
    return this.attributes.has(name) ? (this.attributes.get(name) as string) : null;
  }

  setAttr(name: string, value: string | number | boolean | null): void {
    if (value === null) this.attributes.delete(name);
    else this.setAttribute(name, String(value));
  }

  getAttr(name: string): string | null {
    return this.getAttribute(name);
  }

  appendChild(child: FakeElement): FakeElement {
    child.detach();
    child.parent = this;
    this.children.push(child);
    return child;
  }

  append(...nodes: (FakeElement | string)[]): void {
    for (const node of nodes) {
      if (typeof node === 'string') this.appendChild(new FakeElement('#text')).textContent = node;
      else this.appendChild(node);
    }
  }

  appendText(text: string): void {
    this.append(text);
  }

  createEl(tag: string, info?: DomElementInfoLike | string, callback?: (el: FakeElement) => void): FakeElement {
    const el = new FakeElement(tag);
    if (typeof info === 'string') el.textContent = info;
    else if (info) {
      if (info.text !== undefined) el.textContent = info.text;
      if (info.cls !== undefined) el.addClass(...(Array.isArray(info.cls) ? info.cls : [info.cls]));
      if (info.attr) for (const [k, v] of Object.entries(info.attr)) el.setAttr(k, v);
      if (info.title !== undefined) el.setAttribute('title', info.title);
      if (info.placeholder !== undefined) el.setAttribute('placeholder', info.placeholder);
      if (info.type !== undefined) el.setAttribute('type', info.type);
      if (info.value !== undefined) el.value = info.value;
      if (info.href !== undefined) el.setAttribute('href', info.href);
    }
    this.appendChild(el);
    callback?.(el);
    return el;
  }

  createDiv(info?: DomElementInfoLike | string, callback?: (el: FakeElement) => void): FakeElement {
    return this.createEl('div', info, callback);
  }

  createSpan(info?: DomElementInfoLike | string, callback?: (el: FakeElement) => void): FakeElement {
    return this.createEl('span', info, callback);
  }

  addEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  removeEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    this.listeners.set(type, list.filter((l) => l !== listener));
  }

  dispatchEvent(event: FakeEvent): boolean {
    let prevented = false;
    event.preventDefault ??= () => {
      prevented = true;
      event.defaultPrevented = true;
    };
    event.stopPropagation ??= () => undefined;
    for (const listener of [...(this.listeners.get(event.type) ?? [])]) listener(event);
    return !prevented;
  }

  onClickEvent(listener: Listener): void {
    this.addEventListener('click', listener);
  }

  click(): void {
    if (this.disabled) return;
    this.dispatchEvent({ type: 'click' });
  }

  focus(): void {}
  blur(): void {}
  scrollTo(): void {}

  /** Depth-first search helpers for tests. */
  findAll(predicate: (el: FakeElement) => boolean): FakeElement[] {
    const out: FakeElement[] = [];
    const walk = (el: FakeElement): void => {
      if (predicate(el)) out.push(el);
      for (const child of el.children) walk(child);
    };
    walk(this);
    return out;
  }

  findByText(text: string): FakeElement | undefined {
    return this.findAll((el) => el.children.length === 0 && el.textContent === text)[0];
  }

  listenerCount(type: string): number {
    return (this.listeners.get(type) ?? []).length;
  }
}

/** Create a fake element typed as the DOM `HTMLElement` the real API exposes. */
export function fakeEl(tag = 'div'): HTMLElement {
  return new FakeElement(tag) as unknown as HTMLElement;
}

/** Reverse of `fakeEl` for assertions. */
export function asFake(el: HTMLElement | FakeElement): FakeElement {
  return el as unknown as FakeElement;
}

// ----------------------------------------------------------------------------- state

export interface RecordedCommand {
  id: string;
  name: string;
  callback?: () => unknown;
  checkCallback?: (checking: boolean) => boolean | void;
  icon?: string;
}

export interface MockState {
  notices: string[];
  /** Every `requestUrl` attempt (always rejected). */
  network: unknown[];
  openModals: Modal[];
  /** Value returned by `Plugin.loadData`, set by `saveData`. */
  data: unknown;
  vaultRoot: string;
  vaultName: string;
  configDir: string;
  /** Vault-relative path -> text, backing the fake DataAdapter. */
  adapterFiles: Map<string, string>;
  adapterFolders: Set<string>;
  /** Vault-relative path -> TAbstractFile. */
  files: Map<string, TAbstractFile>;
  reset(): void;
}

export const mockState: MockState = {
  notices: [],
  network: [],
  openModals: [],
  data: null,
  vaultRoot: '/vault',
  vaultName: 'vault',
  configDir: '.obsidian',
  adapterFiles: new Map(),
  adapterFolders: new Set(),
  files: new Map(),
  reset() {
    this.notices = [];
    this.network = [];
    this.openModals = [];
    this.data = null;
    this.vaultRoot = '/vault';
    this.vaultName = 'vault';
    this.configDir = '.obsidian';
    this.adapterFiles = new Map();
    this.adapterFolders = new Set();
    this.files = new Map();
    Object.assign(Platform, DESKTOP_PLATFORM);
  },
};

// ----------------------------------------------------------------------------- platform

const DESKTOP_PLATFORM = {
  isDesktop: true,
  isMobile: false,
  isDesktopApp: true,
  isMobileApp: false,
  isIosApp: false,
  isAndroidApp: false,
  isPhone: false,
  isTablet: false,
  isMacOS: false,
  isWin: process.platform === 'win32',
  isLinux: process.platform === 'linux',
  isSafari: false,
  resourcePathPrefix: 'app://test/',
};

export const Platform: typeof DESKTOP_PLATFORM = { ...DESKTOP_PLATFORM };

/** Simulate the mobile app: `Platform.isDesktop === false`. */
export function simulateMobile(): void {
  Object.assign(Platform, {
    isDesktop: false,
    isMobile: true,
    isDesktopApp: false,
    isMobileApp: true,
    isPhone: true,
    isWin: false,
    isLinux: false,
    isMacOS: false,
    resourcePathPrefix: 'file:///',
  });
}

export function simulateDesktop(): void {
  Object.assign(Platform, DESKTOP_PLATFORM);
}

// ----------------------------------------------------------------------------- events

export interface EventRef {
  name: string;
  callback: (...data: unknown[]) => unknown;
  ctx?: unknown;
  /** Set by `offref`. */
  off: () => void;
}

export class Events {
  readonly handlers = new Map<string, EventRef[]>();

  on(name: string, callback: (...data: never[]) => unknown, ctx?: unknown): EventRef {
    const ref: EventRef = { name, callback: callback as (...data: unknown[]) => unknown, ctx, off: () => this.offref(ref) };
    const list = this.handlers.get(name) ?? [];
    list.push(ref);
    this.handlers.set(name, list);
    return ref;
  }

  off(name: string, callback: (...data: unknown[]) => unknown): void {
    this.handlers.set(name, (this.handlers.get(name) ?? []).filter((r) => r.callback !== callback));
  }

  offref(ref: EventRef): void {
    this.handlers.set(ref.name, (this.handlers.get(ref.name) ?? []).filter((r) => r !== ref));
  }

  trigger(name: string, ...data: unknown[]): void {
    for (const ref of [...(this.handlers.get(name) ?? [])]) ref.callback(...data);
  }

  tryTrigger(evt: EventRef, args: unknown[]): void {
    evt.callback(...args);
  }

  listenerCount(name: string): number {
    return (this.handlers.get(name) ?? []).length;
  }
}

// ----------------------------------------------------------------------------- files

export abstract class TAbstractFile {
  vault!: Vault;
  path: string;
  name: string;
  parent: TFolder | null = null;

  constructor(path: string) {
    this.path = path;
    this.name = path.split('/').pop() ?? path;
  }
}

export class TFile extends TAbstractFile {
  extension: string;
  basename: string;
  stat = { ctime: 0, mtime: 0, size: 0 };

  constructor(path: string) {
    super(path);
    const dot = this.name.lastIndexOf('.');
    this.extension = dot > 0 ? this.name.slice(dot + 1) : '';
    this.basename = dot > 0 ? this.name.slice(0, dot) : this.name;
  }
}

export class TFolder extends TAbstractFile {
  children: TAbstractFile[] = [];

  isRoot(): boolean {
    return this.path === '/' || this.path === '';
  }
}

export interface Stat {
  type: 'file' | 'folder';
  ctime: number;
  mtime: number;
  size: number;
}

export interface ListedFiles {
  files: string[];
  folders: string[];
}

export class FileSystemAdapter {
  getName(): string {
    return 'FileSystemAdapter';
  }

  getBasePath(): string {
    return mockState.vaultRoot;
  }

  getFullPath(normalizedPath: string): string {
    return `${mockState.vaultRoot}/${normalizedPath}`;
  }

  async exists(normalizedPath: string): Promise<boolean> {
    return mockState.adapterFiles.has(normalizedPath) || mockState.adapterFolders.has(normalizedPath);
  }

  async stat(normalizedPath: string): Promise<Stat | null> {
    if (mockState.adapterFiles.has(normalizedPath)) {
      return { type: 'file', ctime: 0, mtime: 0, size: (mockState.adapterFiles.get(normalizedPath) as string).length };
    }
    if (mockState.adapterFolders.has(normalizedPath)) return { type: 'folder', ctime: 0, mtime: 0, size: 0 };
    return null;
  }

  async list(normalizedPath: string): Promise<ListedFiles> {
    const prefix = normalizedPath ? `${normalizedPath}/` : '';
    const direct = (p: string): boolean => p.startsWith(prefix) && !p.slice(prefix.length).includes('/');
    return {
      files: [...mockState.adapterFiles.keys()].filter(direct),
      folders: [...mockState.adapterFolders].filter(direct),
    };
  }

  async read(normalizedPath: string): Promise<string> {
    const text = mockState.adapterFiles.get(normalizedPath);
    if (text === undefined) throw new Error(`ENOENT: ${normalizedPath}`);
    return text;
  }

  async readBinary(normalizedPath: string): Promise<ArrayBuffer> {
    const text = await this.read(normalizedPath);
    return new TextEncoder().encode(text).buffer as ArrayBuffer;
  }

  async write(normalizedPath: string, data: string): Promise<void> {
    mockState.adapterFiles.set(normalizedPath, data);
  }

  async writeBinary(normalizedPath: string, data: ArrayBuffer): Promise<void> {
    mockState.adapterFiles.set(normalizedPath, new TextDecoder().decode(data));
  }

  async append(normalizedPath: string, data: string): Promise<void> {
    mockState.adapterFiles.set(normalizedPath, (mockState.adapterFiles.get(normalizedPath) ?? '') + data);
  }

  async mkdir(normalizedPath: string): Promise<void> {
    mockState.adapterFolders.add(normalizedPath);
  }

  async remove(normalizedPath: string): Promise<void> {
    mockState.adapterFiles.delete(normalizedPath);
  }

  async rmdir(normalizedPath: string): Promise<void> {
    mockState.adapterFolders.delete(normalizedPath);
  }

  async rename(from: string, to: string): Promise<void> {
    const text = mockState.adapterFiles.get(from);
    if (text === undefined) throw new Error(`ENOENT: ${from}`);
    mockState.adapterFiles.delete(from);
    mockState.adapterFiles.set(to, text);
  }

  async trashSystem(): Promise<boolean> {
    return false;
  }

  async trashLocal(): Promise<void> {}

  getResourcePath(normalizedPath: string): string {
    return `${Platform.resourcePathPrefix}${normalizedPath}`;
  }
}

export type DataAdapter = FileSystemAdapter;

export class Vault extends Events {
  adapter: DataAdapter = new FileSystemAdapter();

  get configDir(): string {
    return mockState.configDir;
  }

  getName(): string {
    return mockState.vaultName;
  }

  getAbstractFileByPath(path: string): TAbstractFile | null {
    return mockState.files.get(path) ?? null;
  }

  getFileByPath(path: string): TFile | null {
    const f = this.getAbstractFileByPath(path);
    return f instanceof TFile ? f : null;
  }

  getFolderByPath(path: string): TFolder | null {
    const f = this.getAbstractFileByPath(path);
    return f instanceof TFolder ? f : null;
  }

  getRoot(): TFolder {
    const root = this.getFolderByPath('/');
    if (root) return root;
    const created = new TFolder('/');
    mockState.files.set('/', created);
    return created;
  }

  getFiles(): TFile[] {
    return [...mockState.files.values()].filter((f): f is TFile => f instanceof TFile);
  }

  getAllLoadedFiles(): TAbstractFile[] {
    return [...mockState.files.values()];
  }
}

export class Workspace extends Events {
  layoutReady = true;
  containerEl: HTMLElement = fakeEl('div');

  onLayoutReady(callback: () => unknown): void {
    callback();
  }

  getActiveFile(): TFile | null {
    return null;
  }
}

export class App {
  workspace = new Workspace();
  vault = new Vault();
  metadataCache = new Events();
  fileManager = {};
  lastEvent: unknown = null;

  loadLocalStorage(): unknown {
    return null;
  }

  saveLocalStorage(): void {}
}

// ----------------------------------------------------------------------------- components

export class Component {
  private cleanups: (() => unknown)[] = [];
  private loaded = false;

  /** Marks the component loaded, then runs `onload`; the (possibly async) result is returned so tests can await it. */
  load(): void | Promise<void> {
    if (this.loaded) return;
    this.loaded = true;
    return this.onload();
  }

  onload(): void | Promise<void> {}

  unload(): void {
    if (!this.loaded) return;
    this.loaded = false;
    for (const cleanup of this.cleanups.splice(0).reverse()) cleanup();
    this.onunload();
  }

  onunload(): void {}

  addChild<T extends Component>(component: T): T {
    this.register(() => component.unload());
    component.load();
    return component;
  }

  removeChild<T extends Component>(component: T): T {
    component.unload();
    return component;
  }

  register(cb: () => unknown): void {
    this.cleanups.push(cb);
  }

  registerEvent(eventRef: EventRef): void {
    this.register(() => eventRef.off());
  }

  registerDomEvent(el: HTMLElement | Window | Document, type: string, callback: (evt: never) => unknown): void {
    const target = el as unknown as FakeElement;
    const listener = callback as unknown as Listener;
    target.addEventListener(type, listener);
    this.register(() => target.removeEventListener(type, listener));
  }

  registerInterval(id: number): number {
    this.register(() => clearInterval(id));
    return id;
  }
}

export interface Command {
  id: string;
  name: string;
  icon?: string;
  mobileOnly?: boolean;
  repeatable?: boolean;
  callback?: () => unknown;
  checkCallback?: (checking: boolean) => boolean | void;
  editorCallback?: (...args: unknown[]) => unknown;
  editorCheckCallback?: (...args: unknown[]) => boolean | void;
  hotkeys?: unknown[];
}

export interface PluginManifest {
  id: string;
  name: string;
  author: string;
  version: string;
  minAppVersion: string;
  description: string;
  dir?: string;
  authorUrl?: string;
  isDesktopOnly?: boolean;
}

export class Plugin extends Component {
  app: App;
  manifest: PluginManifest;
  /** Registered commands, in order (ids exactly as passed; the host adds the prefix). */
  readonly commands: Command[] = [];
  readonly ribbons: { icon: string; title: string; callback: (evt: MouseEvent) => unknown; el: HTMLElement }[] = [];
  readonly settingTabs: PluginSettingTab[] = [];
  readonly statusBarItems: HTMLElement[] = [];

  constructor(app: App, manifest: PluginManifest) {
    super();
    this.app = app;
    this.manifest = manifest;
  }

  addCommand(command: Command): Command {
    this.commands.push(command);
    this.register(() => {
      const idx = this.commands.indexOf(command);
      if (idx >= 0) this.commands.splice(idx, 1);
    });
    return command;
  }

  removeCommand(commandId: string): void {
    const idx = this.commands.findIndex((c) => c.id === commandId);
    if (idx >= 0) this.commands.splice(idx, 1);
  }

  addRibbonIcon(icon: string, title: string, callback: (evt: MouseEvent) => unknown): HTMLElement {
    const el = fakeEl('div');
    asFake(el).addEventListener('click', (evt) => callback(evt as unknown as MouseEvent));
    const entry = { icon, title, callback, el };
    this.ribbons.push(entry);
    this.register(() => {
      const idx = this.ribbons.indexOf(entry);
      if (idx >= 0) this.ribbons.splice(idx, 1);
    });
    return el;
  }

  addStatusBarItem(): HTMLElement {
    const el = fakeEl('div');
    this.statusBarItems.push(el);
    return el;
  }

  addSettingTab(settingTab: PluginSettingTab): void {
    this.settingTabs.push(settingTab);
    this.register(() => {
      const idx = this.settingTabs.indexOf(settingTab);
      if (idx >= 0) this.settingTabs.splice(idx, 1);
    });
  }

  async loadData(): Promise<unknown> {
    return mockState.data === null || mockState.data === undefined ? null : JSON.parse(JSON.stringify(mockState.data));
  }

  async saveData(data: unknown): Promise<void> {
    mockState.data = JSON.parse(JSON.stringify(data));
  }

  onUserEnable(): void {}

  /** Run a registered command by id as the host would. */
  runCommand(id: string): boolean {
    const command = this.commands.find((c) => c.id === id);
    if (!command) return false;
    if (command.checkCallback) {
      const ok = command.checkCallback(true);
      if (ok === false) return false;
      command.checkCallback(false);
      return true;
    }
    command.callback?.();
    return true;
  }
}

export class Scope {
  readonly keys: { modifiers: string[] | null; key: string | null }[] = [];

  register(modifiers: string[] | null, key: string | null, _func: unknown): unknown {
    const handler = { modifiers, key };
    this.keys.push(handler);
    return handler;
  }

  unregister(): void {}
}

export class Modal {
  app: App;
  scope = new Scope();
  containerEl: HTMLElement = fakeEl('div');
  modalEl: HTMLElement = fakeEl('div');
  titleEl: HTMLElement = fakeEl('div');
  contentEl: HTMLElement = fakeEl('div');
  shouldRestoreSelection = false;
  isOpen = false;

  constructor(app: App) {
    this.app = app;
    asFake(this.containerEl).appendChild(asFake(this.modalEl));
    asFake(this.modalEl).appendChild(asFake(this.titleEl));
    asFake(this.modalEl).appendChild(asFake(this.contentEl));
  }

  open(): void {
    if (this.isOpen) return;
    this.isOpen = true;
    mockState.openModals.push(this);
    this.onOpen();
  }

  close(): void {
    if (!this.isOpen) return;
    this.isOpen = false;
    const idx = mockState.openModals.indexOf(this);
    if (idx >= 0) mockState.openModals.splice(idx, 1);
    this.onClose();
  }

  onOpen(): void {}

  onClose(): void {}

  setTitle(title: string): this {
    asFake(this.titleEl).setText(title);
    return this;
  }

  setContent(content: string): this {
    asFake(this.contentEl).setText(content);
    return this;
  }
}

export class Notice {
  noticeEl: HTMLElement = fakeEl('div');
  containerEl: HTMLElement = fakeEl('div');
  messageEl: HTMLElement = fakeEl('div');
  message: string;
  hidden = false;

  constructor(message: string | { textContent?: string | null }, readonly duration?: number) {
    this.message = typeof message === 'string' ? message : (message.textContent ?? '');
    asFake(this.messageEl).setText(this.message);
    mockState.notices.push(this.message);
  }

  setMessage(message: string): this {
    this.message = message;
    asFake(this.messageEl).setText(message);
    mockState.notices.push(message);
    return this;
  }

  hide(): void {
    this.hidden = true;
  }
}

export abstract class BaseComponent {
  disabled = false;

  then(cb: (component: this) => unknown): this {
    cb(this);
    return this;
  }

  setDisabled(disabled: boolean): this {
    this.disabled = disabled;
    return this;
  }
}

export class ButtonComponent extends BaseComponent {
  buttonEl: HTMLElement = fakeEl('button');
  text = '';
  cta = false;
  warning = false;

  setButtonText(name: string): this {
    this.text = name;
    asFake(this.buttonEl).setText(name);
    return this;
  }

  setIcon(_icon: string): this {
    return this;
  }

  setTooltip(_tooltip: string): this {
    return this;
  }

  setCta(): this {
    this.cta = true;
    return this;
  }

  removeCta(): this {
    this.cta = false;
    return this;
  }

  setWarning(): this {
    this.warning = true;
    return this;
  }

  setClass(cls: string): this {
    asFake(this.buttonEl).addClass(cls);
    return this;
  }

  override setDisabled(disabled: boolean): this {
    super.setDisabled(disabled);
    asFake(this.buttonEl).disabled = disabled;
    return this;
  }

  onClick(callback: (evt: MouseEvent) => unknown): this {
    asFake(this.buttonEl).addEventListener('click', (evt) => callback(evt as unknown as MouseEvent));
    return this;
  }
}

export class ExtraButtonComponent extends ButtonComponent {
  extraSettingsEl: HTMLElement = this.buttonEl;
}

abstract class ValueComponent<T> extends BaseComponent {
  protected value!: T;
  protected changeListeners: ((value: T) => unknown)[] = [];

  getValue(): T {
    return this.value;
  }

  setValue(value: T): this {
    this.value = value;
    return this;
  }

  onChange(callback: (value: T) => unknown): this {
    this.changeListeners.push(callback);
    return this;
  }

  /** Test helper: simulate user input. */
  simulateChange(value: T): void {
    this.value = value;
    for (const listener of this.changeListeners) listener(value);
  }
}

export class TextComponent extends ValueComponent<string> {
  inputEl: HTMLElement = fakeEl('input');
  placeholder = '';

  constructor() {
    super();
    this.value = '';
    // Like the real component: typing (an `input` DOM event) fires `onChange` with the element value.
    asFake(this.inputEl).addEventListener('input', () => this.simulateChange(asFake(this.inputEl).value));
  }

  setPlaceholder(placeholder: string): this {
    this.placeholder = placeholder;
    return this;
  }

  override setValue(value: string): this {
    super.setValue(value);
    asFake(this.inputEl).value = value;
    return this;
  }
}

export class ToggleComponent extends ValueComponent<boolean> {
  toggleEl: HTMLElement = fakeEl('div');

  constructor() {
    super();
    this.value = false;
  }

  setTooltip(_tooltip: string): this {
    return this;
  }
}

export class DropdownComponent extends ValueComponent<string> {
  selectEl: HTMLElement = fakeEl('select');
  readonly options = new Map<string, string>();

  constructor() {
    super();
    this.value = '';
    // Like the real component: a `change` DOM event fires `onChange` with the element value.
    asFake(this.selectEl).addEventListener('change', () => this.simulateChange(asFake(this.selectEl).value));
  }

  addOption(value: string, display: string): this {
    this.options.set(value, display);
    return this;
  }

  addOptions(options: Record<string, string>): this {
    for (const [k, v] of Object.entries(options)) this.addOption(k, v);
    return this;
  }
}

export class Setting {
  settingEl: HTMLElement;
  infoEl: HTMLElement;
  nameEl: HTMLElement;
  descEl: HTMLElement;
  controlEl: HTMLElement;
  readonly components: BaseComponent[] = [];

  constructor(containerEl: HTMLElement) {
    this.settingEl = asFake(containerEl).createEl('div', { cls: 'setting-item' }) as unknown as HTMLElement;
    this.infoEl = asFake(this.settingEl).createDiv({ cls: 'setting-item-info' }) as unknown as HTMLElement;
    this.nameEl = asFake(this.infoEl).createDiv({ cls: 'setting-item-name' }) as unknown as HTMLElement;
    this.descEl = asFake(this.infoEl).createDiv({ cls: 'setting-item-description' }) as unknown as HTMLElement;
    this.controlEl = asFake(this.settingEl).createDiv({ cls: 'setting-item-control' }) as unknown as HTMLElement;
  }

  setName(name: string): this {
    asFake(this.nameEl).setText(name);
    return this;
  }

  setDesc(desc: string): this {
    asFake(this.descEl).setText(desc);
    return this;
  }

  setHeading(): this {
    asFake(this.settingEl).addClass('setting-item-heading');
    return this;
  }

  setClass(cls: string): this {
    asFake(this.settingEl).addClass(cls);
    return this;
  }

  setTooltip(_tooltip: string): this {
    return this;
  }

  setDisabled(disabled: boolean): this {
    for (const component of this.components) component.setDisabled(disabled);
    return this;
  }

  private add<T extends BaseComponent>(component: T, cb: (component: T) => unknown, el?: HTMLElement): this {
    if (el) asFake(this.controlEl).appendChild(asFake(el));
    this.components.push(component);
    cb(component);
    return this;
  }

  addButton(cb: (component: ButtonComponent) => unknown): this {
    const c = new ButtonComponent();
    return this.add(c, cb, c.buttonEl);
  }

  addExtraButton(cb: (component: ExtraButtonComponent) => unknown): this {
    const c = new ExtraButtonComponent();
    return this.add(c, cb, c.buttonEl);
  }

  addText(cb: (component: TextComponent) => unknown): this {
    const c = new TextComponent();
    return this.add(c, cb, c.inputEl);
  }

  addTextArea(cb: (component: TextComponent) => unknown): this {
    const c = new TextComponent();
    return this.add(c, cb, c.inputEl);
  }

  addToggle(cb: (component: ToggleComponent) => unknown): this {
    const c = new ToggleComponent();
    return this.add(c, cb, c.toggleEl);
  }

  addDropdown(cb: (component: DropdownComponent) => unknown): this {
    const c = new DropdownComponent();
    return this.add(c, cb, c.selectEl);
  }

  then(cb: (setting: this) => unknown): this {
    cb(this);
    return this;
  }
}

export abstract class SettingTab {
  app!: App;
  containerEl: HTMLElement = fakeEl('div');
  abstract display(): void;
  hide(): void {
    asFake(this.containerEl).empty();
  }
}

export abstract class PluginSettingTab extends SettingTab {
  plugin: Plugin;

  constructor(app: App, plugin: Plugin) {
    super();
    this.app = app;
    this.plugin = plugin;
  }
}

export class MenuItem {
  title = '';
  icon: string | null = null;
  disabled = false;
  section = '';
  private clickHandler: ((evt: unknown) => unknown) | null = null;

  setTitle(title: string): this {
    this.title = title;
    return this;
  }

  setIcon(icon: string | null): this {
    this.icon = icon;
    return this;
  }

  setDisabled(disabled: boolean): this {
    this.disabled = disabled;
    return this;
  }

  setSection(section: string): this {
    this.section = section;
    return this;
  }

  setIsLabel(_isLabel: boolean): this {
    return this;
  }

  setChecked(_checked: boolean | null): this {
    return this;
  }

  onClick(callback: (evt: unknown) => unknown): this {
    this.clickHandler = callback;
    return this;
  }

  /** Test helper. */
  click(): void {
    if (!this.disabled) this.clickHandler?.({ type: 'click' });
  }
}

export class Menu extends Component {
  readonly items: MenuItem[] = [];
  readonly separators: number[] = [];
  dom: HTMLElement = fakeEl('div');

  addItem(cb: (item: MenuItem) => unknown): this {
    const item = new MenuItem();
    this.items.push(item);
    cb(item);
    return this;
  }

  addSeparator(): this {
    this.separators.push(this.items.length);
    return this;
  }

  setNoIcon(): this {
    return this;
  }

  setUseNativeMenu(_useNativeMenu: boolean): this {
    return this;
  }

  showAtMouseEvent(_evt: unknown): this {
    return this;
  }

  showAtPosition(_position: unknown): this {
    return this;
  }

  hide(): this {
    return this;
  }

  close(): void {}

  onHide(_callback: () => unknown): void {}
}

// ----------------------------------------------------------------------------- functions

/** Mock App typed as the public `App` so it can be handed to shell code. */
export function createApp(): ObsidianApp {
  return new App() as unknown as ObsidianApp;
}

/** View a shell plugin instance through the mock's recorders. */
export function asMockPlugin(plugin: ObsidianPlugin): Plugin {
  return plugin as unknown as Plugin;
}

/** Manifest for the shell plugin as the host would pass it. */
export function testManifest(overrides: Partial<ObsidianManifest> = {}): ObsidianManifest {
  return {
    id: 'markitdown-flow',
    name: 'MarkItDown Flow',
    author: 'test',
    version: '2.0.0',
    minAppVersion: '1.6.0',
    description: 'Convert local documents to Markdown with OCR planning and selective transcription.',
    dir: '.obsidian/plugins/markitdown-flow',
    isDesktopOnly: true,
    ...overrides,
  };
}

export function normalizePath(path: string): string {
  let out = path.replace(/\\/g, '/').replace(/\/{2,}/g, '/');
  out = out.replace(/^\/+/, '').replace(/\/+$/, '');
  return out === '' ? '/' : out;
}

export function setIcon(_parent: HTMLElement, _iconId: string): void {}

export function addIcon(_iconId: string, _svgContent: string): void {}

export function requestUrl(request: unknown): Promise<never> {
  mockState.network.push(request);
  return Promise.reject(new Error('requestUrl is disabled in shell tests: the shell performs no network calls'));
}

export function debounce<T extends unknown[]>(cb: (...args: T) => unknown): (...args: T) => void {
  return (...args: T) => {
    cb(...args);
  };
}

export const apiVersion = '1.8.7';
