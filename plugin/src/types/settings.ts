export interface ConversionLogEntry {
	inputFile: string;
	outputFile: string;
	timestamp: string; // ISO 8601
	success: boolean;
	error?: string;
	processingTimeMs?: number;
	assetsExtracted?: number;
}

export interface PluginArgEntry {
	key: string;
	value: string;
}

/**
 * All image pipeline parameters with their defaults, stored as JSON.
 * Users can edit this in Settings → Image pipeline → Advanced config.
 * Each key maps directly to a Python wrapper PARAM_SPEC entry.
 */
export const DEFAULT_IMAGE_PIPELINE_CONFIG = JSON.stringify({
	ocr_engines: ['tesseract', 'easyocr'],
	ocr_confidence_threshold: 70,
	enable_ocr_ensemble: true,
	enable_table_extraction: true,
	preprocess_deskew: true,
	deskew_method: 'auto',
	confidence_weight_engine_conf: 0.30,
	confidence_weight_agreement: 0.35,
	confidence_weight_length: 0.15,
	confidence_weight_cleanliness: 0.10,
	confidence_weight_stdev_inv: 0.10,
}, null, 2);

export interface MarkitdownSettings {
	pythonPath: string;
	enablePlugins: boolean;
	pluginArgs: PluginArgEntry[];
	docintelEndpoint: string;
	docintelCredential?: string;
	llmApiKey?: string;
	outputPath: string;
	assetExtractionEnabled: boolean;
	assetSubfolderTemplate: string;
	/**
	 * Optional absolute path used as the root when computing output subfolder
	 * structure. When set, a file at "<inputBasePath>/a/b/c.pdf" is written to
	 * "<outputFolder>/a/b/c.md" instead of "<outputFolder>/c.md".
	 * Leave empty (default) to place every output directly in outputFolder.
	 */
	inputBasePath: string;
	enableBatchProgress: boolean;
	enableContextMenu: boolean;
	enableRecursiveConversion: boolean;
	outputFilenameTemplate: string;
	enableDragDrop: boolean;
	enableAutoFrontmatter: boolean;
	autoTags: string;
	conversionHistory: ConversionLogEntry[];

	// ── SmartImageRouter (M2) ────────────────────────────────────────────
	// Master switch. When false, advanced config is not injected.
	imagePipelineEnabled: boolean;
	// Tesseract-style language code — surfaced in UI for quick access.
	ocrLang: string;
	// JSON string holding all pipeline parameters. Parsed and injected at
	// conversion time. Defaults to DEFAULT_IMAGE_PIPELINE_CONFIG.
	imagePipelineAdvancedConfig: string;
}

export const DEFAULT_SETTINGS: MarkitdownSettings = {
	pythonPath: 'python',
	enablePlugins: false,
	pluginArgs: [],
	docintelEndpoint: '',
	docintelCredential: '',
	llmApiKey: '',
	outputPath: '',
	assetExtractionEnabled: false,
	assetSubfolderTemplate: '{filename}-assets',
	inputBasePath: '',
	enableBatchProgress: true,
	enableContextMenu: true,
	enableRecursiveConversion: false,
	outputFilenameTemplate: '{filename}',
	enableDragDrop: true,
	enableAutoFrontmatter: false,
	autoTags: '',
	conversionHistory: [],

	// SmartImageRouter — master switch off by default.
	imagePipelineEnabled: false,
	ocrLang: 'kor+eng',
	imagePipelineAdvancedConfig: DEFAULT_IMAGE_PIPELINE_CONFIG,
};

export interface ConversionOptions {
	enablePlugins?: boolean;
	pluginArgs?: Record<string, unknown>;
	docintelEndpoint?: string;
	docintelCredential?: string;
	llmApiKey?: string;
	extractAssets?: boolean;
	assetDir?: string;
	postProcess?: {
		settings: MarkitdownSettings;
		inputPath: string;
	};
}

export interface ConversionResult {
	success: boolean;
	outputPath?: string;
	error?: string;
	processingTime?: number;
	assetsExtracted?: number;
}

export interface DependencyStatus {
	pythonInstalled: boolean;
	pythonVersion: string | null;
	markitdownInstalled: boolean;
	markitdownVersion: string | null;
}

export interface TriedPath {
	path: string;
	error: string;
}
