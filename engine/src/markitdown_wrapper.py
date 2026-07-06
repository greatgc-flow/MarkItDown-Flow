#!/usr/bin/env python3
"""
Omni-Data Extraction Engine (MarkItDown Wrapper) - Global Enterprise Edition
================================================================================
A universal Python module that recursively explores all formats of data (archives,
images, documents, etc.) and converts them into a consistent Markdown knowledge base.
Designed for N-time invocations, cross-platform OS safety, and zero-loss extraction.

[Installation Guide & Requirements]
Core Packages (Required):
> pip install markitdown Pillow geopy

Optional AI Packages (Install only what you use; module uses Lazy Loading):
> pip install openai anthropic google-genai
> pip install azure-ai-documentintelligence>=1.0.0   # DocIntel 4.0 GA (2024-11-30)
> pip install azure-ai-contentunderstanding           # Content Understanding (2025-05-01-preview)

[Applied Requirements (MECE Checklist & Global Standard)]
1.  Global Standard & OS Independent: English default logic/comments. I18N (8 languages:
    en, ko, ja, zh, hi, fr, es, ar) support for output UI. Auto system timezone fallback.
    Cross-platform path sanitizer (Windows/Mac/Linux/iOS/Android). Strict UTF-8 enforcement.
2.  No-code & Parameterization: Zero hardcoding. All business logic dynamically controllable
    via JSON parameter specification.
3.  Future-Proof Microsoft Core Alignment: Unknown **kwargs are automatically passed through
    to the MarkItDown core engine, ensuring forward compatibility with future library updates.
4.  AI Target Explicit Mapping & Token Saving: AI/DocIntel/CU is skipped by default for pure text.
    Triggered ONLY IF offline parser fails, OR if the file MIME type matches ai_target_mimes /
    docintel_target_mimes / content_understanding_target_mimes, OR if 'exhaustive_mode' is True.
5.  Independent Phases: Offline, AI, DocIntel, and Content Understanding are decoupled into
    independent error-handled blocks.
6.  Safe Root Logging & I/F Tracing: Logs saved to ~/omnidata_logs. External API calls log
    highly detailed, masked payloads and response lengths for deep interface debugging.
7.  N-Invokable Encapsulation: Fully encapsulated OmniDataPipeline. No sys.exit().
8.  Strict Recursion & Inline Consistency: Archives and Embedded assets (Base64) are physically
    extracted, parsed recursively, and nested INLINE strictly beneath the original node.
9.  Strict Formatting Clean-up: Final markdown is parsed via regex to clean up broken tags.

[API Console Links for Integrations]
- OpenAI (GPT-4o, etc)          : https://platform.openai.com/api-keys
- Anthropic (Claude Sonnet/Opus) : https://console.anthropic.com/settings/keys
- Google (Gemini 2.x)           : https://aistudio.google.com/app/apikey
- Azure Document Intelligence   : https://portal.azure.com/ (AI Foundry > Document Intelligence)
- Azure Content Understanding   : https://portal.azure.com/ (AI Foundry > Content Understanding)

[Parameter Application Guide & Specification (JSON Example)]
{
  "output_lang": "en",           // [str] Output MD UI lang ('en','ko','ja','zh','hi','fr','es','ar'). Default: 'en'
  "timezone_offset": 9.0,        // [float] Target Timezone (e.g., 9.0 for KST). Default: null (System Local Time)
  "exhaustive_mode": false,      // [bool] Force ALL parsing phases (Offline, AI, DocIntel, CU). Default: false
  "extract_archives": true,      // [bool] Recursively extract ZIP/TAR. Default: false
  "max_recursion_depth": 5,      // [int] Limit folder/asset recursion depth. Default: 5

  "ai_target_mimes": [           // [list] Target MIME prefixes for AI LLM Vision/Audio parsing.
    "image/", "audio/", "video/"
  ],

  // ── Azure Document Intelligence (4.0 GA, API 2024-11-30) ──────────────────────────────────
  "docintel_target_mimes": [     // [list] Target MIME prefixes for Azure DocIntel parsing.
    "application/pdf", "application/vnd.", "image/"
  ],
  "docintel_endpoint": "https://my-resource-name.cognitiveservices.azure.com/",
  "docintel_credential": "a1b2c3d4e5f647898a9b0c1d2e3f4a5b",
  "docintel_api_version": "2024-11-30",    // [str] DocIntel REST API version. Default: '2024-11-30' (4.0 GA)
  "docintel_model_id": "prebuilt-layout",  // [str] Model: 'prebuilt-layout'(default), 'prebuilt-read',
                                           //       'prebuilt-invoice', 'prebuilt-receipt', 'prebuilt-contract', etc.

  // ── Azure Content Understanding (2025-05-01-preview) ──────────────────────────────────────
  "content_understanding_endpoint": "https://my-resource-name.cognitiveservices.azure.com/",
  "content_understanding_credential": "a1b2c3d4e5f647898a9b0c1d2e3f4a5b",
  "content_understanding_api_version": "2025-05-01-preview",
  "content_understanding_analyzer_id": "prebuilt-documentAnalyzer",
  "content_understanding_target_mimes": [  // [list] Target MIME prefixes for CU parsing.
    "application/pdf", "image/", "video/", "audio/"
  ],

  // ── LLM AI Clients — N-Client Array for Fallback Logic ────────────────────────────────────
  // Supported client_type: 'openai', 'anthropic', 'gemini'
  // Optional 'endpoint' key overrides the default API base URL (Azure OpenAI, proxies, etc.)
  "ai_clients": [
    {
      "client_type": "openai",
      "api_key": "sk-proj-1234abcd5678efgh9012ijkl3456mnop",
      "model": "gpt-4o"
      // Optional: "endpoint": "https://my-azure-openai.openai.azure.com/"
    },
    {
      "client_type": "anthropic",
      "api_key": "sk-ant-api03-aBcDeFgHiJkLmNoPqRsTuVwXyZ12345",
      "model": "claude-sonnet-4-5"
      // Latest models: claude-opus-4-5, claude-sonnet-4-5, claude-haiku-4-5-20251001
      // Optional: "endpoint": "https://my-proxy.example.com"
    },
    {
      "client_type": "gemini",
      "api_key": "AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
      "model": "gemini-2.0-flash"
      // Latest models: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash
      // Optional: "endpoint": "https://generativelanguage.googleapis.com"
    }
  ],

  "llm_prompt": "Analyze this file in extreme detail.",

  // Any other unknown parameters below are dynamically passed directly to MarkItDown Core
  "pdf_layout": true,
  "pdf_dpi": 300
}
"""
 
 
import argparse
import base64
import json
import os
import re
import sys
import time
import logging
import urllib.parse
import traceback
import hashlib
import mimetypes
import shutil
import zipfile
import tarfile
import tempfile
import copy
from datetime import datetime, timezone, timedelta
 
# ==========================================
# 1. Global Logger (Detailed I/F Debugging)
# ==========================================
 
class LoggerSetup:
    """Thread-safe, detailed debug logger outputting to ~/omnidata_logs."""
    @classmethod
    def get_logger(cls, name="OmniDataEngine") -> logging.Logger:
        logger = logging.getLogger(name)
        if logger.handlers: return logger
        
        logger.setLevel(logging.DEBUG)
        target_dir = os.path.join(os.path.expanduser("~"), "omnidata_logs")
        os.makedirs(target_dir, exist_ok=True)
        log_path = os.path.join(target_dir, f"engine_{datetime.now().strftime('%Y%m%d')}.log")
        
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
 
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger
 
logger = LoggerSetup.get_logger()
 
def mask_secrets(payload_dict: dict) -> dict:
    """Recursively masks sensitive API keys and credentials for safe logging."""
    safe_dict = copy.deepcopy(payload_dict)
    for k, v in safe_dict.items():
        if isinstance(v, str) and any(sec in str(k).lower() for sec in ['key', 'credential', 'token', 'secret']):
            safe_dict[k] = v[:4] + "*" * 8 + v[-4:] if len(v) > 8 else "***"
        elif isinstance(v, dict):
            safe_dict[k] = mask_secrets(v)
        elif isinstance(v, list):
            safe_dict[k] = [mask_secrets(i) if isinstance(i, dict) else i for i in v]
    return safe_dict
 
# ==========================================
# 2. Global Utilities & I18N
# ==========================================
 
I18N = {
    'en': {'virtual': 'Raw Asset Fallback', 'meta': 'Document Properties', 'offline': 'Standard Extraction', 'smart_image': 'Smart Image Pipeline', 'ai': 'Vision Analysis', 'docintel': 'Structured Analysis', 'content_understanding': 'Content Understanding Analysis', 'file': 'Source:', 'summary': 'Content Overview', 'attachments': 'Embedded Asset', 'v_desc': '> Fallback content generated due to empty text extraction.', 'archive': 'Archive Contents'},
    'ko': {'virtual': '원본 데이터 대체본', 'meta': '문서 속성', 'offline': '기본 텍스트 추출', 'smart_image': '스마트 이미지 파이프라인', 'ai': '비전 분석', 'docintel': '구조화 분석', 'content_understanding': '콘텐츠 이해 분석', 'file': '출처:', 'summary': '콘텐츠 개요', 'attachments': '포함된 에셋', 'v_desc': '> 텍스트 추출 결과가 없어 원본 데이터를 기반으로 생성된 대체본입니다.', 'archive': '포함된 파일 목록'},
    'ja': {'virtual': '代替アセット', 'meta': 'ドキュメントプロパティ', 'offline': '標準抽出', 'smart_image': 'スマート画像パイプライン', 'ai': 'ビジョン分析', 'docintel': '構造化分析', 'content_understanding': 'コンテンツ理解分析', 'file': 'ソース:', 'summary': 'コンテンツの概要', 'attachments': '埋め込みアセット', 'v_desc': '> テキストが抽出されなかったため生成された代替コンテンツです。', 'archive': 'アーカイブの内容'},
    'zh': {'virtual': '原始资产回退', 'meta': '文档属性', 'offline': '标准提取', 'smart_image': '智能图像处理', 'ai': '视觉分析', 'docintel': '结构化分析', 'content_understanding': '内容理解分析', 'file': '来源:', 'summary': '内容概述', 'attachments': '嵌入资产', 'v_desc': '> 由于未提取到文本而生成的备用内容。', 'archive': '压缩包内容'},
    'hi': {'virtual': 'कच्चा संपत्ति फ़ॉलबैक', 'meta': 'दस्तावेज़ गुण', 'offline': 'मानक निष्कर्षण', 'smart_image': 'स्मार्ट छवि पाइपलाइन', 'ai': 'विज़न विश्लेषण', 'docintel': 'संरचित विश्लेषण', 'content_understanding': 'सामग्री समझ विश्लेषण', 'file': 'स्रोत:', 'summary': 'सामग्री अवलोकन', 'attachments': 'एम्बेडेड संपत्ति', 'v_desc': '> खाली पाठ निष्कर्षण के कारण उत्पन्न फ़ॉलबैक सामग्री।', 'archive': 'पुरालेख सामग्री'},
    'fr': {'virtual': 'Contenu de Remplacement', 'meta': 'Propriétés du Document', 'offline': 'Extraction Standard', 'smart_image': 'Pipeline Image Intelligent', 'ai': 'Analyse Visuelle', 'docintel': 'Analyse Structurée', 'content_understanding': 'Analyse par Compréhension de Contenu', 'file': 'Source:', 'summary': 'Aperçu du Contenu', 'attachments': 'Actif Intégré', 'v_desc': "> Contenu de remplacement généré en raison de l'absence de texte extrait.", 'archive': "Contenu de l'Archive"},
    'es': {'virtual': 'Contenido de Respaldo', 'meta': 'Propiedades del Documento', 'offline': 'Extracción Estándar', 'smart_image': 'Canalización de Imagen Inteligente', 'ai': 'Análisis Visual', 'docintel': 'Análisis Estructurado', 'content_understanding': 'Análisis de Comprensión de Contenido', 'file': 'Fuente:', 'summary': 'Resumen de Contenido', 'attachments': 'Activo Integrado', 'v_desc': '> Contenido de respaldo generado debido a que no se extrajo texto.', 'archive': 'Contenido del Archivo'},
    'ar': {'virtual': 'محتوى احتياطي للأصول', 'meta': 'خصائص المستند', 'offline': 'استخراج قياسي', 'smart_image': 'خط معالجة الصور الذكي', 'ai': 'تحليل الرؤية', 'docintel': 'تحليل منظم', 'content_understanding': 'تحليل فهم المحتوى', 'file': 'المصدر:', 'summary': 'نظرة عامة على المحتوى', 'attachments': 'أصل مضمن', 'v_desc': '> تم إنشاء محتوى احتياطي بسبب عدم استخراج أي نص.', 'archive': 'محتويات الأرشيف'}
}
 
def get_time_str(offset_hours: float = None, dt: datetime = None) -> str:
    """Returns globally consistent time string. Appends KST if offset is exactly +9.0, otherwise standard UTC offset."""
    dt = dt or datetime.now(timezone.utc)
    if offset_hours is not None:
        tz = timezone(timedelta(hours=offset_hours))
        dt = dt.astimezone(tz)
        tz_name = "KST" if offset_hours == 9.0 else f"UTC{offset_hours:+g}"
        return dt.strftime(f'%Y-%m-%d %H:%M:%S {tz_name}')
    else:
        dt = dt.astimezone()
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
 
def sanitize_path(path_str: str, default_name: str = "assets") -> str:
    """Cross-platform safe path sanitizer."""
    sanitized = [re.sub(r'[<>:"|?*\\x00-\\x1F]', '_', p).strip(' .') for p in re.split(r'[\\/]', os.path.normpath(path_str)) if p]
    return os.path.join(*sanitized) if sanitized else default_name
 
def clean_markdown_formatting(md_text: str) -> str:
    """Cleans up markdown formatting artifacts, dangling tags, and excessive spacing."""
    if not md_text: return md_text
    md_text = re.sub(r'\*\*[ \t]*\n\s*([^\n]+?)\s*\n[ \t]*\*\*', r'**\1**\n', md_text)
    md_text = re.sub(r'\*\*[ \t]*\n\s*([^\n]+?)\s*\*\*', r'**\1** ', md_text)
    md_text = re.sub(r'\*\*\s*([^\n]+?)\s*\n[ \t]*\*\*', r' **\1**\n', md_text)
    md_text = re.sub(r'(?m)^[ \t]*\*\*[ \t]*$', '', md_text)
    md_text = re.sub(r'\*\*\s*\*\*', '', md_text)
    md_text = re.sub(r'\n{4,}', '\n\n\n', md_text)
    return md_text


# ─────────────────────────────────────────────────────────────────────────────
# Common helpers — used by both the engine phases and SmartImageRouter.
# Keep these short; they exist to remove repetition, not to over-abstract.
# ─────────────────────────────────────────────────────────────────────────────

def phase_result(content: str = "", status: str = "Skipped", **extras) -> dict:
    """
    Build the standard phase-result dict consumed by `MarkItDownEngine` and
    rendered by `OmniDataPipeline._format_node`.

    Required keys: 'content', 'status'.
    Optional keys (passed via **extras): 'model', 'confidence', 'method',
    'should_escalate_to_ai', 'details', 'reason', etc.

    Examples:
        return phase_result(content=text, status="Success")
        return phase_result(status=f"Skipped ({reason})")
        return phase_result(status=f"Failed ({e})")
    """
    return {"content": content, "status": status, **extras}


def mime_matches(mime: str, prefixes) -> bool:
    """
    Returns True if `mime` starts with any of `prefixes`. An empty/None
    prefix list means 'match anything', which mirrors how the wrapper's
    `*_target_mimes` config keys are interpreted ("unset == all").
    """
    if not prefixes:
        return True
    return any(mime.startswith(p) for p in prefixes)


def lazy_import(module_name: str, attr: str = None):
    """
    Import a module (and optionally an attribute on it) without raising on
    `ImportError`. Returns the module / attribute, or None if the package
    is not installed.

    Intended for optional dependencies whose absence should degrade the
    pipeline gracefully rather than crash it.
    """
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return getattr(mod, attr) if attr else mod
    except ImportError:
        return None
    except AttributeError:
        return None
 
# ==========================================
# 3. Configuration & Dynamic Validation
# ==========================================
 
class ConfigManager:
    # Strict Engine Core Settings
    PARAM_SPEC = {
        'output_lang': (str, 'en', list(I18N.keys()), "UI language"),
        'timezone_offset': (float, None, None, "Timezone offset (e.g., 9.0 for KST)"),
        'exhaustive_mode': (bool, False, None, "Run ALL phases"),
        'extract_archives': (bool, False, None, "Extract ZIP/TAR"),
        'enable_captions': (bool, False, None, "Inject caption prompt"),
        'max_recursion_depth': (int, 5, None, "Recursion depth limit"),
        'ai_target_mimes': (list, ['image/', 'audio/', 'video/'], None, "Target MIME prefixes for AI parsing"),
        # ── Azure Document Intelligence ────────────────────────────────────────────────────────
        'docintel_target_mimes': (list, ['application/pdf', 'application/vnd.', 'image/'], None, "Target MIME prefixes for DocIntel"),
        'docintel_endpoint': (str, "", None, "Azure DocIntel Endpoint URL"),
        'docintel_credential': (str, "", None, "Azure DocIntel API Key"),
        'docintel_api_version': (str, '2024-11-30', None, "DocIntel REST API version (GA: 2024-11-30)"),
        'docintel_model_id': (str, 'prebuilt-layout', None, "DocIntel model: prebuilt-layout, prebuilt-read, prebuilt-invoice, prebuilt-receipt, prebuilt-contract, etc."),
        # ── Azure Content Understanding ────────────────────────────────────────────────────────
        'content_understanding_endpoint': (str, "", None, "Azure Content Understanding Endpoint URL"),
        'content_understanding_credential': (str, "", None, "Azure Content Understanding API Key"),
        'content_understanding_api_version': (str, '2025-05-01-preview', None, "Content Understanding API version"),
        'content_understanding_analyzer_id': (str, 'prebuilt-documentAnalyzer', None, "Analyzer ID: prebuilt-documentAnalyzer or custom analyzer name"),
        'content_understanding_target_mimes': (list, ['application/pdf', 'image/', 'video/', 'audio/'], None, "Target MIME prefixes for Content Understanding"),
        # ── MarkItDown & Common ────────────────────────────────────────────────────────────────
        'enable_plugins': (bool, False, None, "Enable markitdown third-party plugins"),
        'llm_prompt': (str, "Analyze and extract text.", None, "AI prompt"),
        'pdf_layout': (bool, True, None, "Preserve PDF layout"),
        'pdf_dpi': (int, 300, None, "PDF DPI"),
        'pdf_tables': (str, 'auto', ['auto', 'none', 'always'], "PDF table strategy"),
        'keep_data_uris': (bool, True, None, "Keep Base64 (Required)"),
        'extract_decorations': (bool, True, None, "Extract headers/footers"),
        'convert_strikethrough': (bool, True, None, "Convert strikethrough"),
        'preserve_font_styles': (bool, True, None, "Preserve font styles"),
        'max_image_size': (int, 1024, None, "Max image size"),
        'heading_as_h1': (bool, False, None, "Top headings as H1"),
        'strip_white_spaces': (bool, True, None, "Strip extra spaces"),
        'ignore_scanned_under_text': (bool, True, None, "Ignore scanned background"),
        'ignore_links': (bool, False, None, "Ignore links"),
        'sort_by_position': (bool, True, None, "Sort by physical position"),
        'join_broken_words': (bool, True, None, "Merge broken words"),
        # ── SmartImageRouter (M2 image/table pipeline) ────────────────────────
        'ocr_confidence_threshold':  (int,   70,    None, "Unified OCR confidence below which we escalate to AI (0..100)"),
        'enable_ocr_ensemble':       (bool,  True,  None, "Run all configured OCR engines; False = Tesseract only"),
        'enable_table_extraction':   (bool,  True,  None, "Use img2table (OpenCV) for images classified as 'table'; falls back to OCREnsemble"),
        'ocr_engines':               (list,  ['tesseract', 'easyocr'], None, "OCR engines to try, in order"),
        'preprocess_deskew':         (bool,  True,  None, "Auto-rotate skewed scans before OCR"),
        'deskew_method':             (str,   'auto', ['auto','hough','projection'], "Deskew strategy: auto=Hough→projection fallback, hough=border lines only, projection=brute-force angle scan"),
        'ocr_lang':                  (str,   'kor+eng', None, "OCR language (Tesseract-style 'kor+eng', 'eng', 'jpn', etc.)"),
        # ConfidenceMatrix weights — each in [0, ∞); auto-normalized to sum=1.
        'confidence_weight_engine_conf': (float, 0.30, None, "Weight: mean engine self-reported confidence"),
        'confidence_weight_agreement':   (float, 0.35, None, "Weight: cross-engine text similarity"),
        'confidence_weight_length':      (float, 0.15, None, "Weight: inter-engine output-length consistency"),
        'confidence_weight_cleanliness': (float, 0.10, None, "Weight: fraction of non-garbage characters"),
        'confidence_weight_stdev_inv':   (float, 0.10, None, "Weight: inverse of inter-engine confidence spread"),
    }
 
    @classmethod
    def parse(cls, raw_kwargs: dict):
        engine_config, md_init_args, md_convert_args = {}, {}, {}
        ai_configs = raw_kwargs.pop("ai_clients", []) if isinstance(raw_kwargs.get("ai_clients"), list) else []
 
        # Keywords strictly reserved for our Engine pipeline control
        ENGINE_KEYS = {
            'output_lang', 'timezone_offset', 'exhaustive_mode', 'extract_archives',
            'enable_captions', 'max_recursion_depth', 'ai_target_mimes',
            # Azure DocIntel
            'docintel_target_mimes', 'docintel_endpoint', 'docintel_credential',
            'docintel_api_version', 'docintel_model_id',
            # Azure Content Understanding
            'content_understanding_endpoint', 'content_understanding_credential',
            'content_understanding_api_version', 'content_understanding_analyzer_id',
            'content_understanding_target_mimes',
            # SmartImageRouter (M2)
            'ocr_confidence_threshold',
            'enable_ocr_ensemble', 'enable_table_extraction',
            'ocr_engines',
            'preprocess_deskew', 'deskew_method', 'ocr_lang',
            'confidence_weight_engine_conf', 'confidence_weight_agreement',
            'confidence_weight_length', 'confidence_weight_cleanliness',
            'confidence_weight_stdev_inv',
        }
        
        # Keywords strictly reserved for MarkItDown Constructor (__init__)
        MD_INIT_KEYS = {'llm_client', 'llm_model', 'requests_session', 'enable_plugins'}
 
        # 1. Parse Pre-defined Spec & Route to appropriate Dictionary
        for key, (exp_type, default_val, allowed, _) in cls.PARAM_SPEC.items():
            val = raw_kwargs.pop(key, default_val)
            
            if exp_type == bool and isinstance(val, str): val = val.lower() in ('true', 'yes', '1')
            elif exp_type in (int, float) and isinstance(val, str):
                try: val = exp_type(val)
                except ValueError: val = None
                
            if val is not None and not isinstance(val, exp_type):
                logger.warning(f"[Config] '{key}' Type mismatch. Defaulting to: {default_val}")
                val = default_val
            if allowed and val not in allowed:
                logger.warning(f"[Config] '{key}' Value not allowed. Defaulting to: {default_val}")
                val = default_val
 
            if key in ENGINE_KEYS:
                engine_config[key] = val
            elif key in MD_INIT_KEYS:
                md_init_args[key] = val
            else:
                # All formatting/parsing rules like keep_data_uris drop here safely
                md_convert_args[key] = val
 
        # 2. Dynamic Pass-Through for Future/Unknown args
        for key, val in raw_kwargs.items():
            if key in MD_INIT_KEYS:
                md_init_args[key] = val
                logger.debug(f"[Config] Dynamic Pass-Through (Init): '{key}'")
            else:
                md_convert_args[key] = val
                logger.debug(f"[Config] Dynamic Pass-Through (Convert): '{key}'")
 
        return md_init_args, md_convert_args, ai_configs, engine_config
 
# ==========================================
# 4. Universal Extractors & Processors
# ==========================================
 
class MetadataCollector:
    @staticmethod
    def _get_gps_address(lat, lon):
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="omni_data_engine")
            location = geolocator.reverse((lat, lon))
            return location.address if location else "Unknown Location"
        except Exception: return "Geocoding Failed"
 
    @classmethod
    def extract_from_file(cls, filepath: str, tz_offset: float) -> dict:
        meta = {
            "File_Path": filepath,
            "File_Size_Bytes": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            "Created_At": get_time_str(tz_offset, datetime.fromtimestamp(os.path.getctime(filepath), timezone.utc)) if os.path.exists(filepath) else "Unknown",
            "Modified_At": get_time_str(tz_offset, datetime.fromtimestamp(os.path.getmtime(filepath), timezone.utc)) if os.path.exists(filepath) else "Unknown",
        }
        try:
            with open(filepath, "rb") as f:
                data = f.read()
                meta["SHA256_Hash"] = hashlib.sha256(data).hexdigest()
                exif_data = cls.extract_exif_from_bytes(data)
                if exif_data: meta["EXIF"] = exif_data
        except Exception: pass
        return meta
 
    @classmethod
    def extract_exif_from_bytes(cls, image_bytes: bytes) -> dict:
        try:
            from PIL import Image
            import io
            from PIL.ExifTags import TAGS, GPSTAGS
            image = Image.open(io.BytesIO(image_bytes))
            exif_raw = image._getexif()
            if not exif_raw: return None
            
            exif_data = {}
            for tag_id, value in exif_raw.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "GPSInfo":
                    gps_data = {}
                    for t in value: gps_data[GPSTAGS.get(t, t)] = value[t]
                    exif_data[tag] = gps_data
                else:
                    if isinstance(value, bytes):
                        try: value = value.decode('utf-8', 'ignore')
                        except: value = str(value)
                    exif_data[tag] = str(value)
                    
            if "GPSInfo" in exif_data:
                try:
                    gps = exif_data["GPSInfo"]
                    lat, lon = gps.get("GPSLatitude"), gps.get("GPSLongitude")
                    if lat and lon:
                        lat_val = float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600
                        lon_val = float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600
                        if gps.get("GPSLatitudeRef", "N") == 'S': lat_val = -lat_val
                        if gps.get("GPSLongitudeRef", "E") == 'W': lon_val = -lon_val
                        exif_data["_Calculated_GPS"] = f"{lat_val}, {lon_val}"
                        exif_data["_GPS_Address"] = cls._get_gps_address(lat_val, lon_val)
                except Exception: pass
            return exif_data
        except Exception: return None
 
class AssetProcessor:
    @staticmethod
    def process_inline(md_text: str, asset_dir: str, base_out_dir: str, callback_func, loc: dict):
        """Extracts inline base64 assets. Returns (processed_md, extracted_count)."""
        if not md_text: return md_text, 0
        full_dir = os.path.join(os.path.dirname(asset_dir) if os.path.isabs(asset_dir) else base_out_dir,
                                sanitize_path(os.path.basename(asset_dir)))
        os.makedirs(full_dir, exist_ok=True)
        
        count = 0
        pat_md = re.compile(r'(!?\[(.*?)\])\(data:([^/]+)/([^;]+);base64,([a-zA-Z0-9+/=\s\r\n]+)\)')
        pat_html = re.compile(r'(<img\s+[^>]*src=["\'])(data:([^/]+)/([^;]+);base64,([a-zA-Z0-9+/=\s\r\n]+))(["\'][^>]*>)', re.IGNORECASE)
        
        def save_asset(b64, ext):
            nonlocal count
            count += 1
            b64 = re.sub(r'[\s\r\n]', '', b64)
            b64 += '=' * (len(b64) % 4)
            asset_bytes = base64.b64decode(b64.replace('-', '+').replace('_', '/'))
            filename = f"asset_{count:03d}_{hashlib.md5(asset_bytes).hexdigest()[:8]}.{'jpg' if ext=='jpeg' else ext}"
            filepath = os.path.join(full_dir, filename)
            with open(filepath, "wb") as f: f.write(asset_bytes)
            rel_path = os.path.relpath(filepath, base_out_dir).replace('\\', '/')
            if not rel_path.startswith('.'): rel_path = f"./{rel_path}"
            return urllib.parse.quote(rel_path, safe='/.:'), filepath
 
        def build_inline_block(original_tag, rel_path, filepath):
            child_md = callback_func(filepath)
            res = f"{original_tag}({rel_path})"
            if child_md:
                res += f"\n\n<details>\n<summary>{loc['attachments']} ({os.path.basename(filepath)})</summary>\n\n{child_md}\n\n</details>\n\n"
            return res
 
        def _md_rep(m):
            try:
                rel_path, filepath = save_asset(m.group(5), m.group(4).split('+')[0].lower())
                return build_inline_block(m.group(1), rel_path, filepath)
            except Exception as e:
                logger.warning(f"Markdown Asset Inline Failed: {e}")
                return m.group(0)
 
        def _html_rep(m):
            try:
                rel_path, filepath = save_asset(m.group(5), m.group(4).split('+')[0].lower())
                child_md = callback_func(filepath)
                res = f"{m.group(1)}{rel_path}{m.group(6)}"
                if child_md:
                    res += f"\n\n<details>\n<summary>{loc['attachments']} ({os.path.basename(filepath)})</summary>\n\n{child_md}\n\n</details>\n\n"
                return res
            except Exception as e:
                logger.warning(f"HTML Asset Inline Failed: {e}")
                return m.group(0)

        processed = pat_html.sub(_html_rep, pat_md.sub(_md_rep, md_text))
        return processed, count
 
# ==========================================
# 5. Core Engine
# ==========================================
 
class MarkItDownEngine:
    def __init__(self):
        try:
            from markitdown import MarkItDown
            self.MarkItDown = MarkItDown
        except ImportError:
            self.MarkItDown = None
            logger.error("markitdown module missing. Run `pip install markitdown`.")
 
    def _run_smart_image(self, source: str, cfg: dict) -> dict:
        """
        Offline-first image/table pipeline (see python/image_router.py).

        Returns a dict with the standard phase keys ('content', 'status') plus
        the router's diagnostics ('confidence', 'method', 'should_escalate_to_ai',
        'details'). The 'should_escalate_to_ai' flag is what
        ``run_conversion`` consults to decide whether the AI / DocIntel / CU
        phases should still run for this image.

        We lazy-import the router here so that an environment without OpenCV /
        Tesseract / EasyOCR still loads the wrapper happily; the router itself
        also lazy-imports its heavy dependencies and degrades gracefully.
        """
        try:
            # When the wrapper runs as a script (`python markitdown_wrapper.py …`)
            # the script's directory is on sys.path. When imported from elsewhere
            # we have to add it manually.
            wrapper_dir = os.path.dirname(os.path.abspath(__file__))
            if wrapper_dir not in sys.path:
                sys.path.insert(0, wrapper_dir)
            from image_router import SmartImageRouter
        except Exception as e:
            logger.warning(f"[Phase-SmartImage] Could not import image_router: {e}")
            return phase_result(
                status=f"Skipped (image_router import failed: {e})",
                should_escalate_to_ai=True,
            )

        try:
            res = SmartImageRouter(cfg).route(source)
            details = res.get("details", {}) or {}
            logger.info(
                f"[Phase-SmartImage] kind={details.get('kind')} "
                f"confidence={res.get('confidence')} "
                f"escalate={res.get('should_escalate_to_ai')} "
                f"method={res.get('method')}"
            )
            return res
        except Exception as e:
            logger.error(f"[Phase-SmartImage] Runtime error: {e}")
            return phase_result(status=f"Failed ({e})", should_escalate_to_ai=True)

    def _run_offline(self, source, init_args, conv_args) -> dict:
        logger.debug(f"[Phase-Offline] Processing: {os.path.basename(source)} | Init Kwargs: {mask_secrets(init_args)} | Conv Kwargs: {mask_secrets(conv_args)}")
        kwargs = {k: v for k, v in conv_args.items() if k != 'llm_prompt'}
        try:
            res = self.MarkItDown(**init_args).convert(source, **kwargs)
            text = res.text_content or ""
            logger.debug(f"[Phase-Offline] Result: Success | Output Length: {len(text)} chars")
            return phase_result(content=text, status="Success" if text else "Empty")
        except Exception as e:
            logger.warning(f"[Phase-Offline] Failed ({e}). Attempting Safe-Retry with blank kwargs...")
            try:
                res = self.MarkItDown(**init_args).convert(source)
                text = res.text_content or ""
                return phase_result(content=text, status="Success (Safe Retry)" if text else "Empty")
            except Exception as e2:
                logger.error(f"[Phase-Offline] Safe-Retry Failed: {e2}")
                return phase_result(status=f"Failed ({e2})")
 
    def _run_ai(self, source, init_args, conv_args, ai_configs) -> dict:
        for cfg in ai_configs:
            c_type, api_key = cfg.get('client_type', '').lower(), cfg.get('api_key')
            if not c_type or not api_key: continue

            logger.debug(f"[Phase-AI] Fallback Execution via Client: {c_type} | Source: {os.path.basename(source)} | Client Config: {mask_secrets(cfg)}")
            try:
                client = None
                if c_type == 'openai':
                    # Supports Azure OpenAI via endpoint (api_key=azure_key, endpoint=azure_url)
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url=cfg.get('endpoint') or None)
                elif c_type == 'anthropic':
                    # Supports custom proxy via endpoint
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key, base_url=cfg.get('endpoint') or None)
                elif c_type == 'gemini':
                    # google-genai SDK: supports custom endpoint for Vertex AI or proxy
                    from google import genai
                    endpoint = cfg.get('endpoint')
                    if endpoint:
                        client = genai.Client(api_key=api_key, http_options={'base_url': endpoint})
                    else:
                        client = genai.Client(api_key=api_key)
                else:
                    logger.warning(f"[Phase-AI] Unknown client_type: '{c_type}'. Supported: openai, anthropic, gemini.")
                    continue

                if client:
                    args = copy.deepcopy(init_args)
                    args['llm_client'] = client
                    if 'model' in cfg: args['llm_model'] = cfg['model']
                    # FIX: llm_prompt is a MarkItDown constructor arg, not a convert() arg.
                    # Move it from conv_args into the init args so it is applied correctly.
                    if 'llm_prompt' in conv_args:
                        args['llm_prompt'] = conv_args['llm_prompt']
                    ai_conv_args = {k: v for k, v in conv_args.items() if k != 'llm_prompt'}

                    logger.debug(f"[Phase-AI] Instance Init Args: {mask_secrets(args)} | Conversion Kwargs: {mask_secrets(ai_conv_args)}")
                    res = self.MarkItDown(**args).convert(source, **ai_conv_args)
                    length = len(res.text_content) if res.text_content else 0
                    logger.debug(f"[Phase-AI] Result: Success | Model Used: {cfg.get('model','default')} | Output Length: {length} chars")

                    if res.text_content:
                        return phase_result(
                            content=res.text_content,
                            status="Success",
                            model=f"{c_type} ({cfg.get('model','')})",
                        )
            except Exception as e:
                logger.warning(f"[Phase-AI] AI Client Runtime Error ({c_type}): {e}")
        return phase_result(status="Skipped or Failed")
 
    def _run_docintel(self, source, init_args, conv_args, engine_config) -> dict:
        """
        Azure Document Intelligence 4.0 GA (API 2024-11-30).
        Uses the SDK directly to:
          - Specify the exact API version (default: 2024-11-30)
          - Select the model (default: prebuilt-layout)
          - Request native Markdown output via DocumentContentFormat.MARKDOWN
        Falls back to MarkItDown env-var approach if the SDK is not installed.
        """
        end  = engine_config.get('docintel_endpoint')
        key  = engine_config.get('docintel_credential')
        if not end or not key:
            return phase_result(status="Skipped (No Config Provided)")

        api_version = engine_config.get('docintel_api_version', '2024-11-30')
        model_id    = engine_config.get('docintel_model_id', 'prebuilt-layout')

        logger.debug(
            f"[Phase-DocIntel] Endpoint: {end} | Model: {model_id} | "
            f"API: {api_version} | Source: {os.path.basename(source)}"
        )

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import (
                AnalyzeDocumentRequest, DocumentContentFormat
            )
            from azure.core.credentials import AzureKeyCredential

            client = DocumentIntelligenceClient(
                endpoint=end,
                credential=AzureKeyCredential(key),
                api_version=api_version
            )

            with open(source, "rb") as f:
                file_bytes = f.read()

            poller = client.begin_analyze_document(
                model_id=model_id,
                body=AnalyzeDocumentRequest(bytes_source=file_bytes),  # SDK 1.0.0 GA: 'body' (not 'analyze_request')
                output_content_format=DocumentContentFormat.MARKDOWN   # native MD output (4.0 GA)
            )
            result  = poller.result()
            content = result.content or ""
            length  = len(content)
            logger.debug(
                f"[Phase-DocIntel] Result: Success | Model: {model_id} | "
                f"API: {api_version} | Output Length: {length} chars"
            )
            return phase_result(
                content=content,
                status="Success" if content else "Empty",
                model=f"Azure DI {api_version} / {model_id}",
            )

        except ImportError:
            # SDK not installed — fall back to MarkItDown's built-in env-var approach
            logger.warning(
                "[Phase-DocIntel] azure-ai-documentintelligence>=1.0.0 not installed. "
                "Falling back to MarkItDown env-var approach (API version cannot be controlled)."
            )
            os.environ['AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'] = end
            os.environ['AZURE_DOCUMENT_INTELLIGENCE_KEY']      = key
            try:
                kwargs = {k: v for k, v in conv_args.items() if k != 'llm_prompt'}
                res    = self.MarkItDown(**init_args).convert(source, **kwargs)
                text = res.text_content or ""
                logger.debug(f"[Phase-DocIntel] Fallback Result: Success | Output Length: {len(text)} chars")
                return phase_result(
                    content=text,
                    status="Success (MarkItDown Fallback)" if text else "Empty",
                )
            except Exception as e2:
                logger.error(f"[Phase-DocIntel] Fallback Failed: {e2}")
                return phase_result(status=f"Failed ({e2})")
            finally:
                os.environ.pop('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', None)
                os.environ.pop('AZURE_DOCUMENT_INTELLIGENCE_KEY',      None)

        except Exception as e:
            logger.error(f"[Phase-DocIntel] Runtime Error: {e}")
            return phase_result(status=f"Failed ({e})")

    def _run_content_understanding(self, source, engine_config) -> dict:
        """
        Azure Content Understanding (API 2025-05-01-preview).
        Analyzes documents, images, video, and audio using built-in or custom analyzers.
        Install: pip install azure-ai-contentunderstanding
        """
        end  = engine_config.get('content_understanding_endpoint')
        key  = engine_config.get('content_understanding_credential')
        if not end or not key:
            return phase_result(status="Skipped (No Config Provided)")

        api_version  = engine_config.get('content_understanding_api_version', '2025-05-01-preview')
        analyzer_id  = engine_config.get('content_understanding_analyzer_id', 'prebuilt-documentAnalyzer')

        logger.debug(
            f"[Phase-ContentUnderstanding] Endpoint: {end} | Analyzer: {analyzer_id} | "
            f"API: {api_version} | Source: {os.path.basename(source)}"
        )

        try:
            from azure.ai.contentunderstanding import ContentUnderstandingClient
            from azure.core.credentials import AzureKeyCredential

            client = ContentUnderstandingClient(
                endpoint=end,
                credential=AzureKeyCredential(key),
                api_version=api_version
            )

            with open(source, "rb") as f:
                file_bytes = f.read()
            b64_content = base64.b64encode(file_bytes).decode('utf-8')

            # Submit analysis — SDK accept base64Source or urlSource
            poller = client.begin_analyze(
                analyzer_id=analyzer_id,
                body={"base64Source": b64_content}
            )
            result = poller.result()

            # Extract content — field names may vary by analyzer and SDK version
            content_parts = []
            target = getattr(result, 'result', result)  # some SDK versions wrap in .result

            if hasattr(target, 'contents') and target.contents:
                for item in target.contents:
                    for attr in ('markdown', 'text', 'content', 'value'):
                        val = getattr(item, attr, None)
                        if val:
                            content_parts.append(str(val))
                            break
            for attr in ('text', 'content', 'markdown'):
                if not content_parts:
                    val = getattr(target, attr, None)
                    if val:
                        content_parts.append(str(val))

            # Last-resort: serialize the full result dict for debugging
            if not content_parts:
                try:
                    import json
                    raw = result.as_dict() if hasattr(result, 'as_dict') else vars(result)
                    content_parts.append(
                        "<!-- Azure Content Understanding raw result -->\n```json\n" +
                        json.dumps(raw, ensure_ascii=False, indent=2) +
                        "\n```"
                    )
                except Exception:
                    content_parts.append(str(result))

            content = "\n\n".join(content_parts)
            length  = len(content)
            logger.debug(
                f"[Phase-ContentUnderstanding] Result: Success | Analyzer: {analyzer_id} | "
                f"Output Length: {length} chars"
            )
            return phase_result(
                content=content,
                status="Success" if content else "Empty",
                model=f"Azure CU {api_version} / {analyzer_id}",
            )

        except ImportError:
            logger.error(
                "[Phase-ContentUnderstanding] azure-ai-contentunderstanding not installed. "
                "Run: pip install azure-ai-contentunderstanding"
            )
            return phase_result(status="Failed (Package not installed: azure-ai-contentunderstanding)")
        except Exception as e:
            logger.error(f"[Phase-ContentUnderstanding] Runtime Error: {e}")
            return phase_result(status=f"Failed ({e})")

    def build_virtual_base_md(self, source_path: str, mime_type: str, b64_data: str, loc: dict) -> dict:
        filename = os.path.basename(source_path)
        md = f"> {loc['v_desc']}\n\n"
        md += f"![{filename}](data:{mime_type};base64,{b64_data})\n" if mime_type.startswith('image/') else f"[{filename}](data:{mime_type};base64,{b64_data})\n"
        return phase_result(content=md, status="Virtual_Base64_Fallback")
 
    def run_conversion(self, source, init_args, conv_args, ai_configs, cfg, depth: int = 0) -> dict:
        if not self.MarkItDown: return {"Offline": {"content": "> Error: markitdown missing.", "status": "Error"}}
        loc = I18N.get(cfg.get('output_lang', 'en'), I18N['en'])
        results = {}
        
        mime_type = mimetypes.guess_type(source)[0] or "application/octet-stream"
        
        if cfg.get('enable_captions'):
            conv_args['llm_prompt'] = f"{conv_args.get('llm_prompt', '')}\n\n(Write detailed description wrapped in `<details><summary>📝 AI Caption</summary>...</details>`)"
        
        # 1. Offline Execution Phase
        results['Offline'] = self._run_offline(source, init_args, conv_args)
        offline_failed = not results['Offline'].get('content')

        # 1.5. SmartImageRouter — offline-first image/table pipeline (M2).
        # Runs only for image MIMEs. The router classifies (photo/document/
        # table/diagram/blank), preprocesses, runs an OCR ensemble, computes a
        # unified confidence and tells us whether to escalate to AI. We trust
        # its escalation decision over the legacy "MIME match + offline empty"
        # rule — but only for images.
        is_image = mime_type.startswith('image/')
        if is_image:
            results['SmartImage'] = self._run_smart_image(source, cfg)
            smart_escalate = results['SmartImage'].get('should_escalate_to_ai', True)
            smart_has_content = bool(results['SmartImage'].get('content'))
        else:
            results['SmartImage'] = phase_result(
                status="Skipped (not an image)",
                should_escalate_to_ai=False,
            )
            smart_escalate = False
            smart_has_content = False
        smart_failed = not smart_has_content

        # 2. AI (Vision/Audio) Target Check & Execution
        is_ai_applicable = mime_matches(mime_type, cfg.get('ai_target_mimes'))

        # Decision tree:
        #   - exhaustive_mode → always run AI.
        #   - For images: the router's `should_escalate_to_ai` is authoritative.
        #     If the router resolved the image with high confidence, we skip AI
        #     even if offline was empty (the router IS our offline path for images).
        #   - For non-images: legacy rule — run AI when offline failed AND MIME matches.
        if cfg.get('exhaustive_mode'):
            need_ai = True
        elif is_image:
            need_ai = smart_escalate and is_ai_applicable
        else:
            need_ai = offline_failed and is_ai_applicable

        if need_ai and ai_configs:
            results['Online_AI'] = self._run_ai(source, init_args, conv_args, ai_configs)
        else:
            if cfg.get('exhaustive_mode'):
                reason = "exhaustive mode but no ai_configs supplied" if not ai_configs else "exhaustive mode skip"
            elif is_image:
                reason = ("SmartImageRouter produced high-confidence result"
                          if smart_has_content and not smart_escalate
                          else f"MIME '{mime_type}' not in ai_target_mimes")
            elif results['Offline'].get('content'):
                reason = "File parsed successfully offline"
            else:
                reason = f"MIME '{mime_type}' not in ai_target_mimes"
            results['Online_AI'] = phase_result(status=f"Skipped ({reason})")

        # 3. Azure Document Intelligence Target Check & Execution
        is_doc_applicable = mime_matches(mime_type, cfg.get('docintel_target_mimes'))
        has_docintel_config = bool(cfg.get('docintel_endpoint') and cfg.get('docintel_credential'))

        ai_failed = not results['Online_AI'].get('content')
        # DocIntel runs only when every earlier phase (Offline, SmartImage, AI) failed.
        need_doc = cfg.get('exhaustive_mode') or (
            offline_failed and smart_failed and ai_failed
            and (is_doc_applicable or has_docintel_config)
        )
        if need_doc:
            results['DocIntel'] = self._run_docintel(source, init_args, conv_args, cfg)
        else:
            reason = ("Content already resolved"
                      if (results['Offline'].get('content') or smart_has_content or results['Online_AI'].get('content'))
                      else f"MIME '{mime_type}' not in docintel_target_mimes and no DocIntel config")
            results['DocIntel'] = phase_result(status=f"Skipped ({reason})")

        # 4. Azure Content Understanding Target Check & Execution
        is_cu_applicable  = mime_matches(mime_type, cfg.get('content_understanding_target_mimes'))
        has_cu_config = bool(cfg.get('content_understanding_endpoint') and cfg.get('content_understanding_credential'))

        docintel_failed = not results['DocIntel'].get('content')
        need_cu = cfg.get('exhaustive_mode') or (
            offline_failed and smart_failed and ai_failed and docintel_failed
            and (is_cu_applicable or has_cu_config) and has_cu_config
        )
        if need_cu:
            results['ContentUnderstanding'] = self._run_content_understanding(source, cfg)
        else:
            reason = ("Content already resolved"
                      if any(results[k].get('content') for k in ('Offline', 'SmartImage', 'Online_AI', 'DocIntel'))
                      else ("No Content Understanding config" if not has_cu_config
                            else f"MIME '{mime_type}' not in content_understanding_target_mimes"))
            results['ContentUnderstanding'] = phase_result(status=f"Skipped ({reason})")

        # 5. Zero-Loss Virtual Base Document Fallback (Only for Root level 0)
        if depth == 0 and not any(r.get('content') for r in results.values()) and os.path.exists(source):
            try:
                with open(source, "rb") as f: b64_data = base64.b64encode(f.read()).decode('utf-8')
                results['Virtual_Fallback'] = self.build_virtual_base_md(source, mime_type, b64_data, loc)
                logger.info(f"Generated Virtual Base Fallback for raw asset preservation: {os.path.basename(source)}.")
            except Exception as e:
                logger.error(f"[Engine] Virtual Base MD Fallback Construction Failed: {e}")
        return results
 
# ==========================================
# 6. Pipeline API
# ==========================================
 
class OmniDataPipeline:
    def __init__(self, raw_kwargs: dict):
        self.init_args, self.conv_args, self.ai_configs, self.cfg = ConfigManager.parse(raw_kwargs)
        self.engine = MarkItDownEngine()
        self.loc = I18N.get(self.cfg.get('output_lang', 'en'), I18N['en'])
        self.processed_hashes = set()
        # Running total of inline base64 assets extracted to physical files across all
        # recursive process() invocations. Read by the CLI entry point to report back
        # to the TS layer via stdout JSON (key kept as 'images_extracted' for
        # backwards compatibility with the existing TS converter contract).
        self.asset_count = 0
 
    def _format_node(self, source_path: str, meta: dict, parse_results: dict, is_main: bool = False) -> str:
        out_md = f"\n---\n## {self.loc['file']} {os.path.basename(source_path)}\n\n"
        
        out_md += f"<details>\n<summary>{self.loc['meta']}</summary>\n\n"
        for k, v in meta.items():
            if k == "EXIF":
                out_md += "- EXIF Info:\n"
                for ek, ev in v.items(): out_md += f"  - {ek}: {ev}\n"
            else: out_md += f"- {k}: {v}\n"
        out_md += "\n</details>\n\n"
        out_md += f"### {self.loc['summary']}\n\n"
        
        if "Virtual_Fallback" in parse_results:
            out_md += f"<details open>\n<summary>{self.loc['virtual']} [Virtual_Base64_Fallback]</summary>\n\n"
            out_md += f"{parse_results['Virtual_Fallback']['content']}\n\n</details>\n\n"
            
        for key, title_key in [('Offline', 'offline'), ('SmartImage', 'smart_image'), ('Online_AI', 'ai'), ('DocIntel', 'docintel'), ('ContentUnderstanding', 'content_understanding')]:
            r = parse_results.get(key)
            if not r: continue

            # Build the meta tag — model for AI/DocIntel/CU, confidence + method for SmartImage
            meta_tag = ""
            if 'model' in r:
                meta_tag = f" (Model: {r.get('model')})"
            elif key == 'SmartImage' and r.get('confidence') is not None:
                kind = (r.get('details') or {}).get('kind', '?')
                meta_tag = f" (kind={kind}, confidence={r.get('confidence')}, method={r.get('method', '?')})"

            # Render Details block when: content exists, status indicates an explicit failure, or exhaustive mode is on
            render_statuses = ("Success", "Success (Safe Retry)", "Virtual_Base64_Fallback")
            should_render = (
                r.get('status') in render_statuses
                or "Failed" in r.get('status', '')
                or self.cfg.get('exhaustive_mode')
                or (key == 'SmartImage' and bool(r.get('content')))
                or (key == 'SmartImage' and 'Failed' in r.get('status', ''))
            )
            if should_render:
                open_tag = " open" if is_main and key == 'Offline' else ""
                out_md += f"<details{open_tag}>\n<summary>{self.loc[title_key]} [{r.get('status')}]{meta_tag}</summary>\n\n{r.get('content', '')}\n\n</details>\n\n"
        return out_md
 
    def process(self, source: str, depth: int = 0, base_out_dir: str = None, asset_dir: str = None) -> str:
        if depth > self.cfg.get('max_recursion_depth', 5):
            logger.warning(f"[Pipeline] Max recursion depth exceeded for path: {source}")
            return f"\n> Warning: Max recursion depth exceeded ({os.path.basename(source)})\n\n"
            
        if os.path.exists(source):
            with open(source, 'rb') as f: f_hash = hashlib.md5(f.read()).hexdigest()
            if f_hash in self.processed_hashes: 
                logger.debug(f"[Pipeline] Cyclic dependency or duplicate file ignored: {source}")
                return ""
            self.processed_hashes.add(f_hash)
            
        logger.info(f"Processing Node Pipeline [Depth: {depth}]: {os.path.basename(source)}")
        
        meta = MetadataCollector.extract_from_file(source, self.cfg['timezone_offset'])
        parse_results = self.engine.run_conversion(source, self.init_args, self.conv_args, self.ai_configs, self.cfg, depth)
        
        node_md = self._format_node(source, meta, parse_results, is_main=(depth == 0))
        
        if base_out_dir and asset_dir:
            node_md, extracted_n = AssetProcessor.process_inline(
                md_text=node_md,
                asset_dir=asset_dir,
                base_out_dir=base_out_dir,
                callback_func=lambda p: self.process(p, depth + 1, base_out_dir, asset_dir),
                loc=self.loc
            )
            self.asset_count += extracted_n
            
        if self.cfg.get('extract_archives'):
            is_zip = zipfile.is_zipfile(source)
            is_tar = tarfile.is_tarfile(source) if not is_zip else False
            
            if is_zip or is_tar:
                temp_dir = None
                archive_md = ""
                try:
                    temp_dir = tempfile.mkdtemp(prefix="omni_arch_")
                    if is_zip:
                        with zipfile.ZipFile(source, 'r') as z: z.extractall(temp_dir)
                    elif is_tar:
                        with tarfile.open(source, 'r') as t: t.extractall(temp_dir)
                    
                    for root, _, files in os.walk(temp_dir):
                        for f in sorted(files):
                            child_path = os.path.join(root, f)
                            archive_md += self.process(child_path, depth + 1, base_out_dir, asset_dir)
                            
                except Exception as e:
                    logger.error(f"[Pipeline] Archive Extraction Runtime Error: {e}")
                    archive_md += f"\n> Archive extraction failed: {e}\n"
                finally: 
                    if temp_dir and os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
                
                if archive_md:
                    archive_title = self.loc.get('archive', '📦 Archive Contents')
                    node_md += f"\n<details open>\n<summary>{archive_title} ({os.path.basename(source)})</summary>\n\n{archive_md}\n</details>\n\n"
 
        return node_md
 
# ==========================================
# 7. CLI Entrypoint
# ==========================================
 
def main():
    # ─────────────────────────────────────────────────────────────────────────
    # CLI contract with the TypeScript layer (MarkitdownConverter.ts):
    #   - stdout  : on success, a single JSON line
    #               {"success": true, "assets_extracted": N, "processing_time_ms": M}
    #   - stderr  : on failure, a single JSON line {"error": "...", "type": "..."}
    #   - exit    : 0 = success, 1 = failure
    # All human-readable logs go to ~/omnidata_logs/engine_YYYYMMDD.log (and to the
    # console handler at INFO level). The stdout JSON line is the ONLY thing the TS
    # side parses — do not print anything else to stdout from this function.
    # ─────────────────────────────────────────────────────────────────────────
    start_time = time.time()
    logger.info(f"[{get_time_str()}] Omni-Data Engine Boot Sequence Initiated")
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Input file path to be processed")
    group.add_argument("--url", help="Direct URL to be processed")
    parser.add_argument("--output", required=True, help="Absolute path for the output markdown file")
    parser.add_argument("--extract-assets", default=False, action="store_true", help="Enable inline asset physical extraction")
    parser.add_argument("--asset-dir", default="", help="Directory to save extracted assets")
    parser.add_argument("--enable-plugins", default=False, action="store_true", help="Enable markitdown third-party plugins (entry points)")
    parser.add_argument("--docintel-endpoint", default="", help="Azure DocIntel endpoint (overrides plugin-args)")
    parser.add_argument("--plugin-args", default="{}", help="JSON string of parameter specifications")
    args, _ = parser.parse_known_args()

    logger.info(f"[CLI Initial Arguments] {mask_secrets(vars(args))}")

    full_src = os.path.abspath(args.input) if args.input else args.url
    full_out = os.path.abspath(args.output)

    try:
        raw_kwargs = json.loads(args.plugin_args)
        # CLI flags take precedence over plugin-args JSON
        if args.enable_plugins:
            raw_kwargs['enable_plugins'] = True
        if args.docintel_endpoint:
            raw_kwargs.setdefault('docintel_endpoint', args.docintel_endpoint)
            
        doc_cred = os.environ.get('DOCINTEL_CREDENTIAL')
        if doc_cred:
            raw_kwargs['docintel_credential'] = doc_cred
            
        llm_key = os.environ.get('LLM_API_KEY')
        if llm_key:
            if 'ai_clients' in raw_kwargs and isinstance(raw_kwargs['ai_clients'], list) and len(raw_kwargs['ai_clients']) > 0:
                raw_kwargs['ai_clients'][0]['api_key'] = llm_key
            else:
                raw_kwargs['ai_clients'] = [{'client_type': 'openai', 'api_key': llm_key, 'model': 'gpt-4o'}]

        pipeline = OmniDataPipeline(raw_kwargs)

        master_md = f"---\nSource: {full_src}\nConverted at: {get_time_str(pipeline.cfg.get('timezone_offset'))}\n---\n\n"
        base_dir = os.path.dirname(full_out) if args.extract_assets else None
        ast_dir = args.asset_dir if args.extract_assets else None

        master_md += f"\n<details open Source='{os.path.basename(full_src)}'>\n<summary>Contents</summary>\n\n"
        master_md += pipeline.process(full_src, 0, base_dir, ast_dir)
        master_md += f"\n\n</details>\n"

        # Format Clean-up Phase
        master_md = clean_markdown_formatting(master_md)

        # Ensure UTF-8 physical save for Global standard compliance
        os.makedirs(os.path.dirname(full_out), exist_ok=True)
        with open(full_out, "w", encoding="utf-8") as f: f.write(master_md)

        logger.info(f"SUCCESS | Pipeline Execution Completed. Output saved to: {full_out}")

        # Emit stdout JSON for TS-side parsing (see contract at top of main()).
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(json.dumps({
            "success": True,
            "assets_extracted": pipeline.asset_count,
            "processing_time_ms": elapsed_ms,
        }))
    except Exception as e:
        logger.error(f"FAILURE | Critical Pipeline Exception: {traceback.format_exc()}")
        # Emit stderr JSON the TS layer can parse; never let a stray print to stdout
        # confuse the success-JSON parser on the TS side.
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)
 
if __name__ == "__main__":
    main()