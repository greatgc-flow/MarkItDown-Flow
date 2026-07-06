/**
 * Minimal i18n for the MarkItDown-Flow settings UI.
 *
 * Obsidian exposes the user's locale via `navigator.language` (e.g. "ko-KR",
 * "ja", "zh-TW"). We map the primary tag to one of the eight supported codes.
 * Falls back to English when no match is found.
 *
 * Supported codes: en, ko, ja, zh, hi, fr, es, ar
 */

export type LangCode = 'en' | 'ko' | 'ja' | 'zh' | 'hi' | 'fr' | 'es' | 'ar';

/** Detect locale from browser/Obsidian navigator. */
export function detectLang(): LangCode {
	const nav = (typeof navigator !== 'undefined' && navigator.language) ? navigator.language : 'en';
	const primary = nav.split('-')[0].toLowerCase();
	const map: Record<string, LangCode> = {
		ko: 'ko', ja: 'ja', zh: 'zh', hi: 'hi', fr: 'fr', es: 'es', ar: 'ar',
	};
	return map[primary] ?? 'en';
}

export interface UIStrings {
	// Section headings
	sectionPython:        string;
	sectionConversion:    string;
	sectionBehavior:      string;
	sectionAssets:        string;
	sectionAdvanced:      string;
	sectionImagePipeline: string;

	// Python
	pythonPath:        string;
	pythonPathDesc:    string;

	// Conversion
	outputFolder:           string;
	outputFolderDesc:       string;
	inputBasePath:          string;
	inputBasePathDesc:      string;
	outputFilenameTemplate: string;
	outputFilenameTemplateDesc: string;

	// Behavior
	enableContextMenu:       string;
	enableContextMenuDesc:   string;
	enableDragDrop:          string;
	enableDragDropDesc:      string;
	enableBatchProgress:     string;
	enableBatchProgressDesc: string;
	enableRecursive:         string;
	enableRecursiveDesc:     string;

	// Assets
	assetExtraction:      string;
	assetExtractionDesc:  string;
	assetSubfolder:       string;
	assetSubfolderDesc:   string;

	// Image pipeline
	imagePipeline:               string;
	imagePipelineDesc:           string;
	imagePipelineEnabled:        string;
	imagePipelineEnabledDesc:    string;
	ocrLang:                     string;
	ocrLangDesc:                 string;
	advancedConfig:              string;
	advancedConfigDesc:          string;
	advancedConfigReset:         string;
	selfTest:                    string;
	selfTestDesc:                string;
	selfTestBtn:                 string;

	// Common
	enabled: string;
}

const STRINGS: Record<LangCode, UIStrings> = {
	en: {
		sectionPython:        'Python',
		sectionConversion:    'Conversion',
		sectionBehavior:      'Behavior',
		sectionAssets:        'Asset extraction',
		sectionAdvanced:      'Advanced',
		sectionImagePipeline: 'Image pipeline (SmartImageRouter)',

		pythonPath:     'Python path',
		pythonPathDesc: 'Path to Python executable (e.g., python, python3, or a full path).',

		outputFolder:     'Output folder',
		outputFolderDesc: 'Folder for converted files (relative to vault root). Leave empty for "markitdown-output".',
		inputBasePath:    'Input base path',
		inputBasePathDesc:
			'Optional. When set, the relative path from this root is mirrored in the output folder. ' +
			'Example: base="C:\\\\Docs", input="C:\\\\Docs\\\\2026\\\\Q1\\\\report.pdf" → output is placed under "2026/Q1/".',
		outputFilenameTemplate:     'Output filename template',
		outputFilenameTemplateDesc: 'Variables: {filename}, {ext}, {date}, {datetime}. The .md extension is always appended.',

		enableContextMenu:       'Context menu',
		enableContextMenuDesc:   'Show "Convert with MarkItDown" in the file context menu.',
		enableDragDrop:          'Drag-and-drop conversion',
		enableDragDropDesc:      'Convert files dropped onto the Obsidian window.',
		enableBatchProgress:     'Batch progress dialog',
		enableBatchProgressDesc: 'Show a progress window during folder conversion.',
		enableRecursive:         'Recursive folder conversion',
		enableRecursiveDesc:     'Include files in subfolders when converting a folder.',

		assetExtraction:     'Extract embedded assets',
		assetExtractionDesc: 'Save embedded images and media to disk instead of keeping them as data URIs.',
		assetSubfolder:      'Asset subfolder template',
		assetSubfolderDesc:  'Folder name relative to the output .md file. Use {filename} for the document name.',

		imagePipeline:            'Image pipeline (SmartImageRouter)',
		imagePipelineDesc:        'Offline-first OCR and table extraction for images.',
		imagePipelineEnabled:     'Enable image pipeline',
		imagePipelineEnabledDesc: 'Master switch. Enables OCR and table processing for images.',
		ocrLang:                  'OCR language',
		ocrLangDesc:              'Tesseract language code, e.g. kor+eng, jpn, chi_sim.',
		advancedConfig:           'Advanced config (JSON)',
		advancedConfigDesc:       'All pipeline parameters. Each key maps to a Python PARAM_SPEC entry. Edit directly or reset to defaults.',
		advancedConfigReset:      'Reset to defaults',
		selfTest:     'Self-test',
		selfTestDesc: 'Run the pipeline against four bundled fixtures to verify OCR engines and deskew.',
		selfTestBtn:  'Run self-test',

		enabled: 'Enabled',
	},

	ko: {
		sectionPython:        'Python',
		sectionConversion:    '변환 설정',
		sectionBehavior:      '동작 설정',
		sectionAssets:        '에셋 추출',
		sectionAdvanced:      '고급 설정',
		sectionImagePipeline: '이미지 파이프라인 (SmartImageRouter)',

		pythonPath:     'Python 경로',
		pythonPathDesc: 'Python 실행 파일 경로 (예: python, python3, 또는 전체 경로).',

		outputFolder:     '출력 폴더',
		outputFolderDesc: '변환된 파일을 저장할 폴더 (Vault 루트 기준). 비우면 "markitdown-output".',
		inputBasePath:    '입력 기준 경로',
		inputBasePathDesc:
			'선택 사항. 설정 시, 이 경로를 기준으로 입력 파일의 상대 경로를 계산해 출력 경로를 구조화합니다. ' +
			'예: 기준="C:\\\\Docs", 입력="C:\\\\Docs\\\\2026\\\\Q1\\\\report.pdf" → "2026/Q1/" 하위에 출력.',
		outputFilenameTemplate:     '출력 파일명 템플릿',
		outputFilenameTemplateDesc: '변수: {filename}, {ext}, {date}, {datetime}. .md 확장자는 자동 추가됩니다.',

		enableContextMenu:       '컨텍스트 메뉴',
		enableContextMenuDesc:   '파일 우클릭 메뉴에 "Convert with MarkItDown" 항목을 표시합니다.',
		enableDragDrop:          '드래그 앤 드롭 변환',
		enableDragDropDesc:      'Obsidian 창에 파일을 드래그하면 변환합니다.',
		enableBatchProgress:     '배치 진행 창',
		enableBatchProgressDesc: '폴더 변환 중 진행 상황 창을 표시합니다.',
		enableRecursive:         '하위 폴더 재귀 변환',
		enableRecursiveDesc:     '폴더 변환 시 하위 폴더의 파일도 포함합니다.',

		assetExtraction:     '에셋 추출',
		assetExtractionDesc: '내장된 이미지/미디어를 data URI 대신 파일로 저장합니다.',
		assetSubfolder:      '에셋 하위 폴더 템플릿',
		assetSubfolderDesc:  '출력 .md 파일 기준 상대 경로. {filename}을 문서명으로 대체합니다.',

		imagePipeline:            '이미지 파이프라인 (SmartImageRouter)',
		imagePipelineDesc:        '오프라인 우선 OCR 및 테이블 추출.',
		imagePipelineEnabled:     '이미지 파이프라인 활성화',
		imagePipelineEnabledDesc: '마스터 스위치. OCR 및 테이블 처리를 활성화합니다.',
		ocrLang:                  'OCR 언어',
		ocrLangDesc:              'Tesseract 언어 코드 (예: kor+eng, jpn, chi_sim).',
		advancedConfig:           '고급 설정 (JSON)',
		advancedConfigDesc:       '모든 파이프라인 파라미터. 각 키는 Python PARAM_SPEC 항목에 직접 매핑됩니다.',
		advancedConfigReset:      '기본값으로 초기화',
		selfTest:     '셀프 테스트',
		selfTestDesc: '4개 기본 이미지로 OCR 엔진과 기울기 보정 동작을 검증합니다.',
		selfTestBtn:  '셀프 테스트 실행',

		enabled: '활성화',
	},

	ja: {
		sectionPython:        'Python',
		sectionConversion:    '変換設定',
		sectionBehavior:      '動作設定',
		sectionAssets:        'アセット抽出',
		sectionAdvanced:      '詳細設定',
		sectionImagePipeline: '画像パイプライン (SmartImageRouter)',

		pythonPath:     'Pythonパス',
		pythonPathDesc: 'Python実行ファイルのパス (例: python, python3, またはフルパス)。',

		outputFolder:     '出力フォルダ',
		outputFolderDesc: '変換ファイルの保存先 (Vaultルートからの相対)。空白で "markitdown-output"。',
		inputBasePath:    '入力基準パス',
		inputBasePathDesc:
			'任意。設定すると、このパスを基準にした相対パスで出力フォルダを構造化します。',
		outputFilenameTemplate:     '出力ファイル名テンプレート',
		outputFilenameTemplateDesc: '変数: {filename}, {ext}, {date}, {datetime}。.md拡張子は自動付与。',

		enableContextMenu:       'コンテキストメニュー',
		enableContextMenuDesc:   'ファイルの右クリックメニューに変換オプションを表示します。',
		enableDragDrop:          'ドラッグ＆ドロップ変換',
		enableDragDropDesc:      'Obsidianウィンドウへのファイルドロップで変換します。',
		enableBatchProgress:     'バッチ進捗ダイアログ',
		enableBatchProgressDesc: 'フォルダ変換中に進捗ウィンドウを表示します。',
		enableRecursive:         '再帰的フォルダ変換',
		enableRecursiveDesc:     'フォルダ変換時にサブフォルダも対象にします。',

		assetExtraction:     'アセット抽出',
		assetExtractionDesc: '埋め込み画像をdata URIではなくファイルとして保存します。',
		assetSubfolder:      'アセットサブフォルダテンプレート',
		assetSubfolderDesc:  '出力.mdファイルからの相対パス。{filename}はドキュメント名に置換。',

		imagePipeline:            '画像パイプライン (SmartImageRouter)',
		imagePipelineDesc:        'オフライン優先OCRとテーブル抽出。',
		imagePipelineEnabled:     '画像パイプラインを有効化',
		imagePipelineEnabledDesc: 'マスタースイッチ。OCRとテーブル処理を有効にします。',
		ocrLang:                  'OCR言語',
		ocrLangDesc:              'Tesseract言語コード (例: jpn, kor+eng, chi_sim)。',
		advancedConfig:           '詳細設定 (JSON)',
		advancedConfigDesc:       '全パイプラインパラメータ。各キーはPython PARAM_SPECエントリに直接マップされます。',
		advancedConfigReset:      'デフォルトにリセット',
		selfTest:     'セルフテスト',
		selfTestDesc: '4つの組み込みサンプルでOCRと傾き補正の動作を検証します。',
		selfTestBtn:  'セルフテスト実行',

		enabled: '有効',
	},

	zh: {
		sectionPython:        'Python',
		sectionConversion:    '转换设置',
		sectionBehavior:      '行为设置',
		sectionAssets:        '资源提取',
		sectionAdvanced:      '高级设置',
		sectionImagePipeline: '图像管道 (SmartImageRouter)',

		pythonPath:     'Python路径',
		pythonPathDesc: 'Python可执行文件路径 (例: python, python3 或完整路径)。',

		outputFolder:     '输出文件夹',
		outputFolderDesc: '转换文件的保存目录 (相对于Vault根目录)。留空则使用 "markitdown-output"。',
		inputBasePath:    '输入基准路径',
		inputBasePathDesc: '可选。设置后，输入文件相对于此路径的相对路径将镜像到输出目录结构中。',
		outputFilenameTemplate:     '输出文件名模板',
		outputFilenameTemplateDesc: '变量: {filename}, {ext}, {date}, {datetime}。自动添加.md扩展名。',

		enableContextMenu:       '右键菜单',
		enableContextMenuDesc:   '在文件右键菜单中显示转换选项。',
		enableDragDrop:          '拖放转换',
		enableDragDropDesc:      '将文件拖放到Obsidian窗口时自动转换。',
		enableBatchProgress:     '批量进度对话框',
		enableBatchProgressDesc: '文件夹转换时显示进度窗口。',
		enableRecursive:         '递归文件夹转换',
		enableRecursiveDesc:     '转换文件夹时包含子文件夹中的文件。',

		assetExtraction:     '提取嵌入资源',
		assetExtractionDesc: '将嵌入的图像/媒体保存为文件而非data URI。',
		assetSubfolder:      '资源子文件夹模板',
		assetSubfolderDesc:  '相对于输出.md文件的路径。{filename}替换为文档名。',

		imagePipeline:            '图像管道 (SmartImageRouter)',
		imagePipelineDesc:        '离线优先的OCR和表格提取。',
		imagePipelineEnabled:     '启用图像管道',
		imagePipelineEnabledDesc: '主开关。启用OCR和表格处理。',
		ocrLang:                  'OCR语言',
		ocrLangDesc:              'Tesseract语言代码 (例: chi_sim, kor+eng, jpn)。',
		advancedConfig:           '高级配置 (JSON)',
		advancedConfigDesc:       '所有管道参数。每个键直接映射到Python PARAM_SPEC条目。',
		advancedConfigReset:      '恢复默认值',
		selfTest:     '自检',
		selfTestDesc: '使用四个内置样本验证OCR引擎和纠偏功能。',
		selfTestBtn:  '运行自检',

		enabled: '启用',
	},

	hi: {
		sectionPython:        'Python',
		sectionConversion:    'रूपांतरण सेटिंग',
		sectionBehavior:      'व्यवहार सेटिंग',
		sectionAssets:        'एसेट निष्कर्षण',
		sectionAdvanced:      'उन्नत सेटिंग',
		sectionImagePipeline: 'इमेज पाइपलाइन (SmartImageRouter)',

		pythonPath:     'Python पथ',
		pythonPathDesc: 'Python निष्पादन योग्य फ़ाइल का पथ।',

		outputFolder:     'आउटपुट फ़ोल्डर',
		outputFolderDesc: 'रूपांतरित फ़ाइलों के लिए फ़ोल्डर (Vault रूट से सापेक्ष)। खाली छोड़ें = "markitdown-output"।',
		inputBasePath:    'इनपुट बेस पथ',
		inputBasePathDesc: 'वैकल्पिक। सेट करने पर, इस पथ से सापेक्ष संरचना आउटपुट में दिखाई देगी।',
		outputFilenameTemplate:     'आउटपुट फ़ाइलनाम टेम्प्लेट',
		outputFilenameTemplateDesc: 'चर: {filename}, {ext}, {date}, {datetime}।',

		enableContextMenu:       'संदर्भ मेनू',
		enableContextMenuDesc:   'फ़ाइल राइट-क्लिक मेनू में रूपांतरण विकल्प दिखाएं।',
		enableDragDrop:          'ड्रैग एंड ड्रॉप रूपांतरण',
		enableDragDropDesc:      'Obsidian विंडो पर फ़ाइलें ड्रॉप करने पर रूपांतरण।',
		enableBatchProgress:     'बैच प्रगति संवाद',
		enableBatchProgressDesc: 'फ़ोल्डर रूपांतरण के दौरान प्रगति विंडो दिखाएं।',
		enableRecursive:         'पुनरावर्ती फ़ोल्डर रूपांतरण',
		enableRecursiveDesc:     'फ़ोल्डर रूपांतरण में उपफ़ोल्डर भी शामिल करें।',

		assetExtraction:     'एम्बेडेड एसेट निकालें',
		assetExtractionDesc: 'एम्बेडेड छवियों को data URI के बजाय फ़ाइलों के रूप में सहेजें।',
		assetSubfolder:      'एसेट सबफ़ोल्डर टेम्प्लेट',
		assetSubfolderDesc:  'आउटपुट .md से सापेक्ष पथ। {filename} = दस्तावेज़ नाम।',

		imagePipeline:            'इमेज पाइपलाइन',
		imagePipelineDesc:        'ऑफलाइन OCR और तालिका निष्कर्षण।',
		imagePipelineEnabled:     'इमेज पाइपलाइन सक्षम करें',
		imagePipelineEnabledDesc: 'मास्टर स्विच।',
		ocrLang:                  'OCR भाषा',
		ocrLangDesc:              'Tesseract भाषा कोड (जैसे: hin, eng)।',
		advancedConfig:           'उन्नत कॉन्फ़िग (JSON)',
		advancedConfigDesc:       'सभी पाइपलाइन पैरामीटर। प्रत्येक कुंजी Python PARAM_SPEC से मैप होती है।',
		advancedConfigReset:      'डिफ़ॉल्ट पर रीसेट',
		selfTest:     'स्व-परीक्षण',
		selfTestDesc: 'OCR इंजन और डिस्क्यू की जांच करें।',
		selfTestBtn:  'स्व-परीक्षण चलाएं',

		enabled: 'सक्षम',
	},

	fr: {
		sectionPython:        'Python',
		sectionConversion:    'Paramètres de conversion',
		sectionBehavior:      'Comportement',
		sectionAssets:        'Extraction des ressources',
		sectionAdvanced:      'Paramètres avancés',
		sectionImagePipeline: 'Pipeline image (SmartImageRouter)',

		pythonPath:     'Chemin Python',
		pythonPathDesc: 'Chemin de l\'exécutable Python (ex. python, python3 ou chemin complet).',

		outputFolder:     'Dossier de sortie',
		outputFolderDesc: 'Dossier pour les fichiers convertis (relatif à la racine du Vault). Vide = "markitdown-output".',
		inputBasePath:    'Chemin de base d\'entrée',
		inputBasePathDesc: 'Optionnel. Quand défini, le chemin relatif depuis cette racine est reproduit dans le dossier de sortie.',
		outputFilenameTemplate:     'Modèle de nom de fichier de sortie',
		outputFilenameTemplateDesc: 'Variables : {filename}, {ext}, {date}, {datetime}. L\'extension .md est ajoutée automatiquement.',

		enableContextMenu:       'Menu contextuel',
		enableContextMenuDesc:   'Afficher l\'option de conversion dans le menu contextuel des fichiers.',
		enableDragDrop:          'Conversion par glisser-déposer',
		enableDragDropDesc:      'Convertir les fichiers déposés sur la fenêtre Obsidian.',
		enableBatchProgress:     'Dialogue de progression par lot',
		enableBatchProgressDesc: 'Afficher une fenêtre de progression lors de la conversion de dossier.',
		enableRecursive:         'Conversion récursive de dossier',
		enableRecursiveDesc:     'Inclure les sous-dossiers lors de la conversion d\'un dossier.',

		assetExtraction:     'Extraire les ressources intégrées',
		assetExtractionDesc: 'Enregistrer les images en tant que fichiers plutôt que data URI.',
		assetSubfolder:      'Modèle de sous-dossier de ressources',
		assetSubfolderDesc:  'Chemin relatif au fichier .md de sortie. {filename} = nom du document.',

		imagePipeline:            'Pipeline image (SmartImageRouter)',
		imagePipelineDesc:        'OCR hors ligne et extraction de tableaux.',
		imagePipelineEnabled:     'Activer le pipeline image',
		imagePipelineEnabledDesc: 'Interrupteur principal.',
		ocrLang:                  'Langue OCR',
		ocrLangDesc:              'Code de langue Tesseract (ex. fra, kor+eng).',
		advancedConfig:           'Config avancée (JSON)',
		advancedConfigDesc:       'Tous les paramètres du pipeline. Chaque clé correspond à un PARAM_SPEC Python.',
		advancedConfigReset:      'Réinitialiser par défaut',
		selfTest:     'Auto-test',
		selfTestDesc: 'Tester le pipeline sur quatre images de référence.',
		selfTestBtn:  'Lancer l\'auto-test',

		enabled: 'Activé',
	},

	es: {
		sectionPython:        'Python',
		sectionConversion:    'Configuración de conversión',
		sectionBehavior:      'Comportamiento',
		sectionAssets:        'Extracción de recursos',
		sectionAdvanced:      'Configuración avanzada',
		sectionImagePipeline: 'Pipeline de imagen (SmartImageRouter)',

		pythonPath:     'Ruta de Python',
		pythonPathDesc: 'Ruta al ejecutable de Python (ej. python, python3 o ruta completa).',

		outputFolder:     'Carpeta de salida',
		outputFolderDesc: 'Carpeta para los archivos convertidos (relativa a la raíz del Vault). Vacío = "markitdown-output".',
		inputBasePath:    'Ruta base de entrada',
		inputBasePathDesc: 'Opcional. Si se configura, la ruta relativa desde esta raíz se replica en la carpeta de salida.',
		outputFilenameTemplate:     'Plantilla de nombre de archivo de salida',
		outputFilenameTemplateDesc: 'Variables: {filename}, {ext}, {date}, {datetime}. La extensión .md se añade automáticamente.',

		enableContextMenu:       'Menú contextual',
		enableContextMenuDesc:   'Mostrar opción de conversión en el menú contextual de archivos.',
		enableDragDrop:          'Conversión por arrastrar y soltar',
		enableDragDropDesc:      'Convertir archivos soltados en la ventana de Obsidian.',
		enableBatchProgress:     'Diálogo de progreso por lotes',
		enableBatchProgressDesc: 'Mostrar ventana de progreso durante la conversión de carpetas.',
		enableRecursive:         'Conversión recursiva de carpetas',
		enableRecursiveDesc:     'Incluir subcarpetas al convertir una carpeta.',

		assetExtraction:     'Extraer recursos incrustados',
		assetExtractionDesc: 'Guardar imágenes como archivos en lugar de data URI.',
		assetSubfolder:      'Plantilla de subcarpeta de recursos',
		assetSubfolderDesc:  'Ruta relativa al archivo .md de salida. {filename} = nombre del documento.',

		imagePipeline:            'Pipeline de imagen (SmartImageRouter)',
		imagePipelineDesc:        'OCR sin conexión y extracción de tablas.',
		imagePipelineEnabled:     'Activar pipeline de imagen',
		imagePipelineEnabledDesc: 'Interruptor principal.',
		ocrLang:                  'Idioma OCR',
		ocrLangDesc:              'Código de idioma Tesseract (ej. spa, kor+eng).',
		advancedConfig:           'Config avanzada (JSON)',
		advancedConfigDesc:       'Todos los parámetros del pipeline. Cada clave corresponde a un PARAM_SPEC de Python.',
		advancedConfigReset:      'Restablecer valores predeterminados',
		selfTest:     'Autotest',
		selfTestDesc: 'Probar el pipeline con cuatro imágenes de referencia.',
		selfTestBtn:  'Ejecutar autotest',

		enabled: 'Activado',
	},

	ar: {
		sectionPython:        'Python',
		sectionConversion:    'إعدادات التحويل',
		sectionBehavior:      'إعدادات السلوك',
		sectionAssets:        'استخراج الأصول',
		sectionAdvanced:      'إعدادات متقدمة',
		sectionImagePipeline: 'خط أنابيب الصور (SmartImageRouter)',

		pythonPath:     'مسار Python',
		pythonPathDesc: 'مسار ملف Python التنفيذي.',

		outputFolder:     'مجلد الإخراج',
		outputFolderDesc: 'مجلد الملفات المحوَّلة (نسبة إلى جذر الخزنة). اتركه فارغاً لـ "markitdown-output".',
		inputBasePath:    'مسار المدخلات الأساسي',
		inputBasePathDesc: 'اختياري. عند التعيين، يتم نسخ هيكل المجلدات النسبي في مجلد الإخراج.',
		outputFilenameTemplate:     'قالب اسم ملف الإخراج',
		outputFilenameTemplateDesc: 'المتغيرات: {filename}, {ext}, {date}, {datetime}.',

		enableContextMenu:       'قائمة السياق',
		enableContextMenuDesc:   'عرض خيار التحويل في قائمة السياق للملفات.',
		enableDragDrop:          'التحويل بالسحب والإفلات',
		enableDragDropDesc:      'تحويل الملفات عند إسقاطها على نافذة Obsidian.',
		enableBatchProgress:     'نافذة تقدم الدُفعة',
		enableBatchProgressDesc: 'عرض نافذة تقدم أثناء تحويل المجلدات.',
		enableRecursive:         'تحويل المجلدات بشكل متكرر',
		enableRecursiveDesc:     'تضمين المجلدات الفرعية عند تحويل مجلد.',

		assetExtraction:     'استخراج الأصول المضمَّنة',
		assetExtractionDesc: 'حفظ الصور كملفات بدلاً من data URI.',
		assetSubfolder:      'قالب المجلد الفرعي للأصول',
		assetSubfolderDesc:  'مسار نسبي لملف .md الناتج. {filename} = اسم المستند.',

		imagePipeline:            'خط أنابيب الصور',
		imagePipelineDesc:        'OCR غير متصل واستخراج الجداول.',
		imagePipelineEnabled:     'تفعيل خط أنابيب الصور',
		imagePipelineEnabledDesc: 'المفتاح الرئيسي.',
		ocrLang:                  'لغة OCR',
		ocrLangDesc:              'كود لغة Tesseract (مثال: ara, kor+eng).',
		advancedConfig:           'إعداد متقدم (JSON)',
		advancedConfigDesc:       'جميع معاملات خط الأنابيب. كل مفتاح يرتبط بإدخال PARAM_SPEC في Python.',
		advancedConfigReset:      'إعادة تعيين القيم الافتراضية',
		selfTest:     'الاختبار الذاتي',
		selfTestDesc: 'اختبار خط الأنابيب على أربع صور مرجعية.',
		selfTestBtn:  'تشغيل الاختبار الذاتي',

		enabled: 'مفعَّل',
	},
};

/** Return the UI string table for the detected (or specified) locale. */
export function getStrings(lang?: LangCode): UIStrings {
	return STRINGS[lang ?? detectLang()];
}
