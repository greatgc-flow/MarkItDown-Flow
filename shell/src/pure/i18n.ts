/**
 * Code-keyed message table and independently authored en/ko dictionaries
 * (20_SHELL.md REQ-SHL-19). Engine rows are generated from SPEC 7.5's active
 * Code-column cells (codes.ts); JT-SHL-19-01 asserts set equality.
 *
 * Placeholders are `{name}` and are interpolated exactly once with literal text.
 */
import { ENGINE_CODES, type EngineCode, isKnownEngineCode } from './codes';
import type { Locale } from './settings';

export type UiLocale = 'en' | 'ko';

/** Shell diagnostic keys fixed by 20_SHELL.md section 6. */
export type ShellDiagnosticKey =
  | 'shell.SETTINGS'
  | 'shell.RUNTIME'
  | 'shell.PROTOCOL'
  | 'shell.DESTINATION'
  | 'shell.BUSY'
  | 'shell.CANCELLED'
  | 'shell.LEGACY_URL';

export const ENGINE_UNKNOWN_KEY = 'engine.UNKNOWN';

export interface MessageRef {
  key: string;
  /** Fixed, already-redacted parameters; never a raw engine `message`. */
  params: Record<string, string>;
}

const ENGINE_EN: Record<EngineCode, string> = {
  E_USAGE: 'Engine arguments are invalid. Review settings/diagnostics.',
  E_CORE_VERSION: 'Unsupported Core version. Open setup diagnostics.',
  E_PROVIDER_CONFIG: 'Provider configuration is invalid. Check settings/environment.',
  E_SNIFF_IO: 'Cannot read this source. Check access.',
  E_TOO_LARGE: 'Source exceeds the byte limit. Review limits.',
  E_ENCRYPTED: 'Source is protected. Export an unprotected copy.',
  E_CORRUPT: 'Source could not be parsed. Check the original.',
  E_UNSUPPORTED: 'This format is unsupported. Export a supported format.',
  E_MEDIA_OUT_OF_SCOPE: 'Audio/video conversion is unavailable in 2.0.',
  E_LEGACY: 'Legacy format requires external export to a supported format.',
  E_ZIP_PATH: 'Unsafe archive-member path was refused.',
  E_ZIP_DEPTH: 'Archive nesting exceeds the limit.',
  E_ZIP_ENTRIES: 'Archive entry count exceeds the limit.',
  E_ZIP_TOTAL: 'Expanded archive size exceeds the limit.',
  E_ZIP_BOMB: 'Unsafe archive expansion was refused.',
  E_TRIAGE_FAIL: 'OCR inspection failed. Review the conversion report.',
  E_TRIAGE_SCHEMA: 'Unsupported inspection schema. Check engine/Core compatibility.',
  E_CONVERT_FAIL: 'Base conversion failed. Other reported results may remain usable.',
  E_RENDER_FAIL: 'An OCR unit could not be rendered. Review pending work.',
  E_PLAN_OVERSIZE: 'OCR work exceeds the unit limit. Review the pending Plan.',
  E_OUTPUT_IO: 'Output could not be written. Check destination/access.',
  E_OUTPUT_COLLISION: 'Sources map to the same output. Rename inputs or change the selection.',
  E_CACHE_IO: 'Cache could not be written. Review diagnostics before retrying.',
  E_APPROVAL_REQUIRED: 'OCR work is pending your approval. Review the Plan.',
  E_APPROVAL_DENIED: 'OCR was not approved. Pending output is retained.',
  E_PROVIDER_HTTP: 'Provider request failed. Review diagnostics before retrying.',
  E_PROVIDER_TIMEOUT: 'Provider request timed out. Review before retrying.',
  E_PROVIDER_OUTPUT: 'Provider returned unusable text. Review before retrying.',
  W_SKIPPED_HIDDEN: 'Hidden entry skipped.',
  W_SKIPPED_SYMLINK: 'Symbolic link skipped.',
  W_DUPLICATE_INPUT: 'Repeated input skipped; its first occurrence is retained.',
  W_EXT_MISMATCH: 'File content differs from its extension.',
  W_MEDIA_NOT_INSPECTED: 'Some media was not inspected.',
  W_TRIAGE_UNSUPPORTED: 'OCR inspection is unavailable for this format.',
  W_TRIAGE_UNKNOWN: 'OCR need remains unknown.',
  W_TRIAGE_INCONSISTENT: 'Inspection evidence is inconsistent; review required.',
  W_TRIAGE_UNKNOWN_VALUE: 'Inspection returned an unknown value; review compatibility.',
  W_TRIAGE_PARTIAL: 'Inspection is incomplete; more OCR work may exist.',
  W_CORE_DEPENDENCY: 'Core inspection dependency is unavailable. Open setup diagnostics.',
  W_EXTERNAL_MEDIA: 'External media was not fetched or inspected.',
  W_UNRESOLVED_EMBED: 'Embedded media could not be resolved.',
  W_IMAGE_PROBE: 'Image inspection failed; OCR eligibility needs review.',
  W_REVIEW_PRIORITY: 'Low-priority OCR candidates need review.',
  W_MEDIA_UNMAPPED: 'OCR media has no inline anchor; review the unmapped appendix.',
  W_MEDIA_FORMAT: 'Media encoding cannot be used for OCR.',
  W_MEDIA_MULTIFRAME: 'Embedded multi-frame media has limited processing; review the report.',
  W_CACHE_CORRUPT: 'Invalid cache entry ignored; work may need repeating.',
  W_OUTPUT_TRUNCATED: 'Provider text exceeded the output limit and was truncated.',
  W_OUTPUT_EDITED: 'Existing output was edited and was preserved.',
  W_APPROVAL_UNUSED: 'An approved hash was unused; the file may already be cached.',
};

const ENGINE_KO: Record<EngineCode, string> = {
  E_USAGE: '엔진 인수가 잘못되었습니다. 설정과 진단 정보를 확인하세요.',
  E_CORE_VERSION: '지원하지 않는 Core 버전입니다. 설정 진단 창을 열어 확인하세요.',
  E_PROVIDER_CONFIG: '공급자 구성이 잘못되었습니다. 설정과 환경 변수를 확인하세요.',
  E_SNIFF_IO: '이 원본 파일을 읽을 수 없습니다. 접근 권한을 확인하세요.',
  E_TOO_LARGE: '원본 크기가 바이트 한도를 넘었습니다. 한도 설정을 확인하세요.',
  E_ENCRYPTED: '원본이 보호되어 있습니다. 보호를 해제한 사본을 내보내 주세요.',
  E_CORRUPT: '원본을 해석할 수 없습니다. 원본 파일 상태를 확인하세요.',
  E_UNSUPPORTED: '지원하지 않는 형식입니다. 지원되는 형식으로 내보내 주세요.',
  E_MEDIA_OUT_OF_SCOPE: '2.0에서는 오디오/비디오 변환을 제공하지 않습니다.',
  E_LEGACY: '구형 형식은 외부에서 지원 형식으로 먼저 내보내야 합니다.',
  E_ZIP_PATH: '안전하지 않은 압축 항목 경로가 거부되었습니다.',
  E_ZIP_DEPTH: '압축 파일의 중첩 깊이가 한도를 넘었습니다.',
  E_ZIP_ENTRIES: '압축 파일의 항목 수가 한도를 넘었습니다.',
  E_ZIP_TOTAL: '압축 해제 후 전체 크기가 한도를 넘었습니다.',
  E_ZIP_BOMB: '안전하지 않은 압축 확장이 거부되었습니다.',
  E_TRIAGE_FAIL: 'OCR 검사에 실패했습니다. 변환 보고서를 확인하세요.',
  E_TRIAGE_SCHEMA: '지원하지 않는 검사 스키마입니다. 엔진과 Core의 호환성을 확인하세요.',
  E_CONVERT_FAIL: '기본 변환에 실패했습니다. 보고된 다른 결과는 계속 사용할 수 있습니다.',
  E_RENDER_FAIL: 'OCR 단위를 렌더링할 수 없습니다. 대기 중인 작업을 확인하세요.',
  E_PLAN_OVERSIZE: 'OCR 작업량이 단위 한도를 넘었습니다. 대기 중인 Plan을 확인하세요.',
  E_OUTPUT_IO: '출력을 기록할 수 없습니다. 대상 폴더와 접근 권한을 확인하세요.',
  E_OUTPUT_COLLISION: '여러 원본이 같은 출력 경로로 겹칩니다. 입력 이름을 바꾸거나 선택을 조정하세요.',
  E_CACHE_IO: '캐시를 기록할 수 없습니다. 다시 시도하기 전에 진단 정보를 확인하세요.',
  E_APPROVAL_REQUIRED: 'OCR 작업이 승인을 기다리고 있습니다. Plan을 검토하세요.',
  E_APPROVAL_DENIED: 'OCR이 승인되지 않았습니다. 대기 상태의 출력은 그대로 유지됩니다.',
  E_PROVIDER_HTTP: '공급자 요청이 실패했습니다. 다시 시도하기 전에 진단 정보를 확인하세요.',
  E_PROVIDER_TIMEOUT: '공급자 요청 시간이 초과되었습니다. 다시 시도하기 전에 확인하세요.',
  E_PROVIDER_OUTPUT: '공급자가 사용할 수 없는 텍스트를 반환했습니다. 다시 시도하기 전에 확인하세요.',
  W_SKIPPED_HIDDEN: '숨김 항목을 건너뛰었습니다.',
  W_SKIPPED_SYMLINK: '심볼릭 링크를 건너뛰었습니다.',
  W_DUPLICATE_INPUT: '중복된 입력을 건너뛰었습니다. 처음 나온 항목만 유지됩니다.',
  W_EXT_MISMATCH: '파일 내용이 확장자와 다릅니다.',
  W_MEDIA_NOT_INSPECTED: '일부 미디어가 검사되지 않았습니다.',
  W_TRIAGE_UNSUPPORTED: '이 형식은 OCR 검사를 지원하지 않습니다.',
  W_TRIAGE_UNKNOWN: 'OCR 필요 여부를 판단할 수 없습니다.',
  W_TRIAGE_INCONSISTENT: '검사 근거가 서로 어긋납니다. 검토가 필요합니다.',
  W_TRIAGE_UNKNOWN_VALUE: '검사 결과에 알 수 없는 값이 있습니다. 호환성을 검토하세요.',
  W_TRIAGE_PARTIAL: '검사가 완료되지 않았습니다. 추가 OCR 작업이 있을 수 있습니다.',
  W_CORE_DEPENDENCY: 'Core 검사에 필요한 구성 요소를 사용할 수 없습니다. 설정 진단 창을 열어 확인하세요.',
  W_EXTERNAL_MEDIA: '외부 미디어는 가져오거나 검사하지 않았습니다.',
  W_UNRESOLVED_EMBED: '포함된 미디어를 찾을 수 없습니다.',
  W_IMAGE_PROBE: '이미지 검사에 실패했습니다. OCR 대상 여부를 검토해야 합니다.',
  W_REVIEW_PRIORITY: '우선순위가 낮은 OCR 후보가 검토를 기다리고 있습니다.',
  W_MEDIA_UNMAPPED: 'OCR 미디어에 본문 위치가 없습니다. 미배치 부록을 확인하세요.',
  W_MEDIA_FORMAT: '이 미디어 인코딩은 OCR에 사용할 수 없습니다.',
  W_MEDIA_MULTIFRAME: '포함된 다중 프레임 미디어는 일부만 처리됩니다. 보고서를 확인하세요.',
  W_CACHE_CORRUPT: '손상된 캐시 항목을 무시했습니다. 작업을 다시 해야 할 수 있습니다.',
  W_OUTPUT_TRUNCATED: '공급자 텍스트가 출력 한도를 넘어 잘렸습니다.',
  W_OUTPUT_EDITED: '기존 출력이 수정되어 있어 그대로 보존했습니다.',
  W_APPROVAL_UNUSED: '승인된 해시가 사용되지 않았습니다. 파일이 이미 캐시되어 있을 수 있습니다.',
};

const SHELL_EN: Record<string, string> = {
  'engine.UNKNOWN': 'Unrecognized engine diagnostic ({code}). Review compatibility.',
  'shell.SETTINGS': 'Settings could not be migrated/saved; conversion is blocked.',
  'shell.RUNTIME': 'Engine unavailable or incompatible. Open setup diagnostics.',
  'shell.PROTOCOL': 'Invalid engine response; this run did not complete successfully.',
  'shell.DESTINATION': 'Choose an output directory inside this vault.',
  'shell.BUSY': 'A conversion is already active.',
  'shell.CANCELLED': 'Conversion interrupted; review results before retrying.',
  'shell.LEGACY_URL': 'URL import is unavailable; save locally and convert the file.',
  'shell.setup.apiKeyMissing': 'MDFLOW_API_KEY is not set in the Obsidian process. Local conversion with provider none remains available; remote OCR is blocked until Obsidian is launched from a terminal where the variable is set.',
  'shell.migration.header': 'Settings were migrated from version 1. {count} preference changes were applied:',
  'shell.migration.incompatible': 'The settings file was written by a newer plugin version. Settings are read-only and conversion is blocked until the plugin is updated.',
  'shell.migration.unknownKeys': '- {count} unknown settings were discarded.',
  'shell.migration.action.dropped': '{key} was removed ({count}).',
  'shell.migration.action.reset': '{key} was invalid and reset to its default ({count}).',
  'shell.migration.action.hint': '{key} was kept only as a terminal-instruction hint ({count}).',
  'shell.migration.action.skipped': '{key}: {count} invalid entries were skipped.',
  'shell.migration.action.discarded': '{key}: {count} entries were discarded.',
  'shell.migration.key.pythonPath': 'Select the venv interpreter as enginePython in settings; the old interpreter is never executed automatically.',
  'shell.migration.key.enablePlugins': 'Third-party Core plugin loading is unavailable.',
  'shell.migration.key.pluginArgs': 'Wrapper arguments were not imported; command providers are CLI-only.',
  'shell.migration.key.docintelEndpoint': 'Built-in Azure DocIntel/CU support was removed; an external command recipe is available.',
  'shell.migration.key.docintelCredential': 'The stored credential was removed. Use the selected provider environment variable instead.',
  'shell.migration.key.llmApiKey': 'The stored API key was removed; the provider remains none. Use the MDFLOW_API_KEY environment variable.',
  'shell.migration.key.assetExtractionEnabled': 'Engine-required media publication is always enabled.',
  'shell.migration.key.assetSubfolderTemplate': 'The engine writes linked media in a media folder beside the output.',
  'shell.migration.key.inputBasePath': 'Selected inputs define the engine roots; the old mirroring preference is unavailable.',
  'shell.migration.key.outputFilenameTemplate': 'The engine names outputs <original-name>.<ext>.md; the shell does not rename outputs.',
  'shell.migration.key.enableAutoFrontmatter': 'Minimal engine provenance is mandatory; existing notes are untouched.',
  'shell.migration.key.autoTags': 'Version 2 has no tag option; tags were not added to output.',
  'shell.migration.key.imagePipelineEnabled': 'Per-unit Plans replace the old image router.',
  'shell.migration.key.ocrLang': 'Tesseract language codes do not configure the version 2 provider.',
  'shell.migration.key.imagePipelineAdvancedConfig': 'Old ensemble, confidence, table and deskew tuning is unavailable.',
  'shell.consent.title': 'Approve remote OCR for this selection',
  'shell.consent.billing': 'Requests that are interrupted or fail before the cache is written may already have been billed by the provider; retrying can duplicate that cost. Shared images may be sent once per request budget and are not guaranteed to be deduplicated across concurrent jobs.',
  'shell.consent.destinationDir': 'Output directory: {dir}',
  'shell.consent.file': 'File',
  'shell.consent.sha256': 'Source SHA-256',
  'shell.consent.planHash': 'Plan hash',
  'shell.consent.provider': 'Provider / model',
  'shell.consent.destination': 'Destination',
  'shell.consent.selectedUnits': 'Selected units',
  'shell.consent.dpi': 'DPI',
  'shell.consent.pendingLowPriority': 'Pending low-priority units',
  'shell.consent.cacheStatus': 'Cache (informational): {cached} cached, {toSend} to send',
  'shell.consent.budget': 'Approved request budget',
  'shell.consent.estMaxCost': 'Estimated maximum cost (USD)',
  'shell.consent.unknownCost': 'unknown',
  'shell.consent.thresholdExceeded': 'Threshold exceeded: this file needs more unique images than the approval threshold.',
  'shell.consent.sensitiveHits': 'Sensitive pattern matches: {hits}',
  'shell.consent.acknowledge': 'Approving acknowledges the threshold, sensitive-pattern and unknown-cost notices for the files shown.',
  'shell.consent.keepPending': 'Keep pending',
  'shell.consent.approve': 'Approve this selection',
  'shell.history.title': 'Conversion history',
  'shell.history.empty': 'No conversions recorded.',
  'shell.history.clear': 'Clear history',
  'shell.history.outcome.complete': 'completed',
  'shell.history.outcome.pending_consent': 'pending consent',
  'shell.history.outcome.partial_failure': 'partial failure',
  'shell.history.outcome.cancelled': 'cancelled',
  'shell.history.outcome.legacy': 'legacy entry',
  'shell.setup.title': 'Engine setup diagnostics',
  'shell.setup.interpreter': 'Engine interpreter',
  'shell.setup.unconfigured': 'No engine interpreter is configured. Follow the terminal instructions below, then choose the venv interpreter in settings.',
  'shell.setup.versions': 'Versions',
  'shell.setup.probe': 'Probe status',
  'shell.setup.probeOk': 'ready',
  'shell.setup.probeBlocked': 'blocked ({reason})',
  'shell.setup.bootstrapProbes': 'Bootstrap interpreters found',
  'shell.setup.instructions': 'Run these commands in your own terminal (the plugin never installs anything)',
  'shell.setup.copyWindows': 'Copy PowerShell commands',
  'shell.setup.copyPosix': 'Copy shell commands',
  'shell.setup.copyDiagnostics': 'Copy diagnostics',
  'shell.setup.refresh': 'Re-run version check',
  'shell.setup.apiKey': 'MDFLOW_API_KEY in the Obsidian process: {presence}',
  'shell.setup.launchHint': 'Desktop launches may not inherit terminal variables: fully quit Obsidian, set the variable in a terminal and start Obsidian from that terminal.',
  'shell.settings.enginePython': 'Engine interpreter (absolute venv python)',
  'shell.settings.outputPath': 'Output folder (inside this vault)',
  'shell.settings.enableBatchProgress': 'Show progress details',
  'shell.settings.enableContextMenu': 'Add file and folder context-menu actions',
  'shell.settings.enableRecursiveConversion': 'Convert folders recursively',
  'shell.settings.enableDragDrop': 'Convert dropped local files',
  'shell.settings.locale': 'Language',
  'shell.settings.provider': 'OCR provider',
  'shell.settings.model': 'Model',
  'shell.settings.baseUrl': 'Base URL',
  'shell.settings.openSetup': 'Open setup diagnostics',
  'shell.settings.keyNote': 'Credentials come only from the MDFLOW_API_KEY environment variable; nothing is stored here.',
  'shell.ribbon.title': 'Convert documents to Markdown',
  'shell.menu.convert': 'Convert to Markdown (MarkItDown Flow)',
  'shell.command.convertFile': 'Convert file(s) to Markdown',
  'shell.command.convertFolder': 'Convert folder to Markdown',
  'shell.command.convertUrl': 'Convert URL (unavailable: save locally first)',
  'shell.command.history': 'View conversion history',
  'shell.command.logs': 'Open log folder',
  'shell.command.selftest': 'Run engine self-test',
  'shell.notice.logsNote': 'Logs are plugin-local and redacted; old logs remain in ~/omnidata_logs and are not managed by this version.',
  'shell.notice.selftestOk': 'Engine self-test passed.',
  'shell.notice.jobDone': 'Conversion finished: {outcome}.',
  'shell.drop.confirm': 'Convert {count} dropped file(s)?',
};

const SHELL_KO: Record<string, string> = {
  'engine.UNKNOWN': '알 수 없는 엔진 진단 코드입니다 ({code}). 호환성을 검토하세요.',
  'shell.SETTINGS': '설정을 이전하거나 저장할 수 없어 변환이 차단되었습니다.',
  'shell.RUNTIME': '엔진을 사용할 수 없거나 호환되지 않습니다. 설정 진단 창을 열어 확인하세요.',
  'shell.PROTOCOL': '엔진 응답이 올바르지 않습니다. 이번 실행은 정상적으로 완료되지 않았습니다.',
  'shell.DESTINATION': '이 보관소 안에 있는 출력 폴더를 선택하세요.',
  'shell.BUSY': '이미 진행 중인 변환이 있습니다.',
  'shell.CANCELLED': '변환이 중단되었습니다. 다시 시도하기 전에 결과를 확인하세요.',
  'shell.LEGACY_URL': 'URL 가져오기는 지원하지 않습니다. 파일을 로컬에 저장한 뒤 변환하세요.',
  'shell.setup.apiKeyMissing': 'Obsidian 프로세스에 MDFLOW_API_KEY가 설정되어 있지 않습니다. 공급자 none으로 로컬 변환은 계속 사용할 수 있으며, 변수가 설정된 터미널에서 Obsidian을 실행할 때까지 원격 OCR은 차단됩니다.',
  'shell.migration.header': '버전 1 설정을 이전했습니다. 변경된 환경설정 항목 {count}개:',
  'shell.migration.incompatible': '설정 파일이 더 새로운 플러그인 버전으로 저장되었습니다. 플러그인을 업데이트하기 전까지 설정은 읽기 전용이며 변환은 차단됩니다.',
  'shell.migration.unknownKeys': '- 알 수 없는 설정 {count}개를 버렸습니다.',
  'shell.migration.action.dropped': '{key} 항목을 제거했습니다 ({count}).',
  'shell.migration.action.reset': '{key} 값이 올바르지 않아 기본값으로 되돌렸습니다 ({count}).',
  'shell.migration.action.hint': '{key} 값은 터미널 안내 문구의 힌트로만 유지합니다 ({count}).',
  'shell.migration.action.skipped': '{key}: 올바르지 않은 항목 {count}개를 건너뛰었습니다.',
  'shell.migration.action.discarded': '{key}: 항목 {count}개를 버렸습니다.',
  'shell.migration.key.pythonPath': '설정에서 venv 인터프리터를 enginePython으로 직접 선택하세요. 이전 인터프리터는 자동으로 실행되지 않습니다.',
  'shell.migration.key.enablePlugins': '타사 Core 플러그인 불러오기는 더 이상 제공되지 않습니다.',
  'shell.migration.key.pluginArgs': '래퍼 인수는 가져오지 않았습니다. 명령 공급자는 CLI에서만 사용할 수 있습니다.',
  'shell.migration.key.docintelEndpoint': '내장 Azure DocIntel/CU 지원이 제거되었습니다. 외부 명령 레시피를 사용할 수 있습니다.',
  'shell.migration.key.docintelCredential': '저장된 자격 증명을 제거했습니다. 선택한 공급자의 환경 변수를 사용하세요.',
  'shell.migration.key.llmApiKey': '저장된 API 키를 제거했으며 공급자는 none으로 유지됩니다. MDFLOW_API_KEY 환경 변수를 사용하세요.',
  'shell.migration.key.assetExtractionEnabled': '엔진이 요구하는 미디어 게시는 항상 켜져 있습니다.',
  'shell.migration.key.assetSubfolderTemplate': '엔진은 연결된 미디어를 출력 옆의 media 폴더에 기록합니다.',
  'shell.migration.key.inputBasePath': '선택한 입력이 엔진 루트를 결정하며, 이전의 미러링 설정은 제공되지 않습니다.',
  'shell.migration.key.outputFilenameTemplate': '엔진은 출력 이름을 <원본 이름>.<확장자>.md 형식으로 정하며, 셸은 출력 이름을 바꾸지 않습니다.',
  'shell.migration.key.enableAutoFrontmatter': '최소한의 엔진 출처 정보는 필수이며 기존 노트는 수정하지 않습니다.',
  'shell.migration.key.autoTags': '버전 2에는 태그 옵션이 없으며 출력에 태그를 추가하지 않습니다.',
  'shell.migration.key.imagePipelineEnabled': '단위별 Plan이 이전 이미지 라우터를 대체합니다.',
  'shell.migration.key.ocrLang': 'Tesseract 언어 코드는 버전 2 공급자를 설정하지 않습니다.',
  'shell.migration.key.imagePipelineAdvancedConfig': '이전의 앙상블, 신뢰도, 표, 기울기 보정 조정 기능은 제공되지 않습니다.',
  'shell.consent.title': '선택한 파일의 원격 OCR 승인',
  'shell.consent.billing': '캐시에 기록되기 전에 중단되거나 실패한 요청은 이미 공급자에게 과금되었을 수 있으며, 다시 시도하면 비용이 중복될 수 있습니다. 공유 이미지는 요청 예산만큼 전송될 수 있고 동시 작업 간 중복 제거가 보장되지 않습니다.',
  'shell.consent.destinationDir': '출력 폴더: {dir}',
  'shell.consent.file': '파일',
  'shell.consent.sha256': '원본 SHA-256',
  'shell.consent.planHash': 'Plan 해시',
  'shell.consent.provider': '공급자 / 모델',
  'shell.consent.destination': '전송 대상',
  'shell.consent.selectedUnits': '선택된 단위 수',
  'shell.consent.dpi': 'DPI',
  'shell.consent.pendingLowPriority': '보류된 낮은 우선순위 단위',
  'shell.consent.cacheStatus': '캐시(참고용): 캐시됨 {cached}, 전송 예정 {toSend}',
  'shell.consent.budget': '승인되는 요청 예산',
  'shell.consent.estMaxCost': '예상 최대 비용(USD)',
  'shell.consent.unknownCost': '알 수 없음',
  'shell.consent.thresholdExceeded': '임계값 초과: 이 파일의 고유 이미지 수가 승인 임계값보다 많습니다.',
  'shell.consent.sensitiveHits': '민감 패턴 일치: {hits}',
  'shell.consent.acknowledge': '승인하면 표시된 파일에 대한 임계값, 민감 패턴, 비용 미확정 안내를 확인한 것으로 간주합니다.',
  'shell.consent.keepPending': '보류 유지',
  'shell.consent.approve': '이 선택 승인',
  'shell.history.title': '변환 기록',
  'shell.history.empty': '기록된 변환이 없습니다.',
  'shell.history.clear': '기록 지우기',
  'shell.history.outcome.complete': '완료',
  'shell.history.outcome.pending_consent': '승인 대기',
  'shell.history.outcome.partial_failure': '일부 실패',
  'shell.history.outcome.cancelled': '취소됨',
  'shell.history.outcome.legacy': '이전 버전 항목',
  'shell.setup.title': '엔진 설정 진단',
  'shell.setup.interpreter': '엔진 인터프리터',
  'shell.setup.unconfigured': '엔진 인터프리터가 설정되지 않았습니다. 아래 터미널 안내를 따른 뒤 설정에서 venv 인터프리터를 선택하세요.',
  'shell.setup.versions': '버전',
  'shell.setup.probe': '점검 상태',
  'shell.setup.probeOk': '준비됨',
  'shell.setup.probeBlocked': '차단됨 ({reason})',
  'shell.setup.bootstrapProbes': '발견된 부트스트랩 인터프리터',
  'shell.setup.instructions': '다음 명령을 사용자 터미널에서 직접 실행하세요 (플러그인은 아무것도 설치하지 않습니다)',
  'shell.setup.copyWindows': 'PowerShell 명령 복사',
  'shell.setup.copyPosix': '셸 명령 복사',
  'shell.setup.copyDiagnostics': '진단 정보 복사',
  'shell.setup.refresh': '버전 확인 다시 실행',
  'shell.setup.apiKey': 'Obsidian 프로세스의 MDFLOW_API_KEY: {presence}',
  'shell.setup.launchHint': '바탕화면 실행은 터미널 변수를 물려받지 못할 수 있습니다. Obsidian을 완전히 종료한 뒤 터미널에서 변수를 설정하고 그 터미널에서 Obsidian을 실행하세요.',
  'shell.settings.enginePython': '엔진 인터프리터 (venv python의 절대 경로)',
  'shell.settings.outputPath': '출력 폴더 (이 보관소 안)',
  'shell.settings.enableBatchProgress': '진행 상세 표시',
  'shell.settings.enableContextMenu': '파일/폴더 컨텍스트 메뉴 동작 추가',
  'shell.settings.enableRecursiveConversion': '폴더를 재귀적으로 변환',
  'shell.settings.enableDragDrop': '끌어다 놓은 로컬 파일 변환',
  'shell.settings.locale': '언어',
  'shell.settings.provider': 'OCR 공급자',
  'shell.settings.model': '모델',
  'shell.settings.baseUrl': '기본 URL',
  'shell.settings.openSetup': '설정 진단 열기',
  'shell.settings.keyNote': '자격 증명은 MDFLOW_API_KEY 환경 변수로만 전달되며 여기에는 아무것도 저장되지 않습니다.',
  'shell.ribbon.title': '문서를 Markdown으로 변환',
  'shell.menu.convert': 'Markdown으로 변환 (MarkItDown Flow)',
  'shell.command.convertFile': '파일을 Markdown으로 변환',
  'shell.command.convertFolder': '폴더를 Markdown으로 변환',
  'shell.command.convertUrl': 'URL 변환 (지원 안 함: 먼저 로컬에 저장)',
  'shell.command.history': '변환 기록 보기',
  'shell.command.logs': '로그 폴더 열기',
  'shell.command.selftest': '엔진 자체 점검 실행',
  'shell.notice.logsNote': '로그는 플러그인 폴더에 저장되며 민감 정보가 제거됩니다. 이전 로그는 ~/omnidata_logs에 남아 있으며 이 버전에서 관리하지 않습니다.',
  'shell.notice.selftestOk': '엔진 자체 점검을 통과했습니다.',
  'shell.notice.jobDone': '변환이 끝났습니다: {outcome}.',
  'shell.drop.confirm': '끌어다 놓은 파일 {count}개를 변환할까요?',
};

function build(engine: Record<EngineCode, string>, shell: Record<string, string>): Readonly<Record<string, string>> {
  const out: Record<string, string> = {};
  for (const code of ENGINE_CODES) out[`engine.${code}`] = engine[code];
  for (const [key, text] of Object.entries(shell)) out[key] = text;
  return Object.freeze(out);
}

const DICTIONARIES: Record<UiLocale, Readonly<Record<string, string>>> = {
  en: build(ENGINE_EN, SHELL_EN),
  ko: build(ENGINE_KO, SHELL_KO),
};

const PLACEHOLDER = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

/** Active engine codes of the message table (E_/W_), excluding the UNKNOWN fallback. */
export function engineCodeKeys(): readonly string[] {
  return ENGINE_CODES;
}

export function dictionary(locale: UiLocale): Readonly<Record<string, string>> {
  return DICTIONARIES[locale];
}

/** `auto`: `ko*` -> ko, otherwise en; explicit values override the host language. */
export function resolveLocale(setting: Locale, hostLanguage: string | undefined): UiLocale {
  if (setting === 'en' || setting === 'ko') return setting;
  return hostLanguage !== undefined && /^ko(?![a-z])/i.test(hostLanguage) ? 'ko' : 'en';
}

export function isEngineCode(code: string): boolean {
  return isKnownEngineCode(code);
}

/** Literal code made safe for display: identifier characters only, bounded length. */
function redactCode(code: string): string {
  const safe = code.replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 64);
  return safe.length > 0 ? safe : '?';
}

/** Known code -> `engine.<CODE>`; unknown -> `engine.UNKNOWN` with a redacted literal code. */
export function messageForCode(code: string, _rawMessage?: string): MessageRef {
  // The raw engine `message` is intentionally never interpolated (REQ-SHL-19).
  if (isKnownEngineCode(code)) return { key: `engine.${code}`, params: {} };
  return { key: ENGINE_UNKNOWN_KEY, params: { code: redactCode(code) } };
}

/** Interpolate `{name}` placeholders once; parameter values are inserted literally. */
export function formatMessage(locale: UiLocale, key: string, params: Record<string, string> = {}): string {
  const template = DICTIONARIES[locale][key];
  if (template === undefined) return key;
  return template.replace(PLACEHOLDER, (_match, name: string) => params[name] ?? '');
}
