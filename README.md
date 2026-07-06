# 🌟 MarkItDown Flow (Enterprise Edition)

![MarkItDown Flow Banner](https://img.shields.io/badge/MarkItDown-Flow-blue?style=for-the-badge&logo=markdown)
![Obsidian](https://img.shields.io/badge/Obsidian-Plugin-7A3CEF?style=for-the-badge&logo=obsidian)
![Python](https://img.shields.io/badge/Python-3.10%2B-FFD43B?style=for-the-badge&logo=python)

**MarkItDown Flow**는 이미지, PDF, 오디오, 비디오, 압축 파일(ZIP) 등 모든 형태의 데이터를 완벽한 Markdown(마크다운)으로 변환해주는 강력한 통합 엔진 및 Obsidian 플러그인입니다. 

단순 텍스트 추출을 넘어, **4단계 지능형 Fallback 파이프라인**(Offline OCR ➔ AI Vision ➔ Azure DocIntel ➔ Azure Content Understanding)을 통해 데이터 손실 없는 무손실(Zero-loss) 마크다운 변환을 보장합니다.

---

## ✨ 핵심 기능 (Key Features)

- 📴 **강력한 오프라인 엔진 (Phase 1)**: Tesseract, EasyOCR 등 앙상블 OCR을 활용한 빠르고 비용 없는 오프라인 텍스트 추출.
- 🤖 **스마트 AI 비전 폴백 (Phase 2)**: 오프라인 추출 실패 시 또는 복잡한 이미지에 대해 **OpenAI (GPT-4o), Anthropic (Claude), Google (Gemini)** 비전 모델로 자동 우회.
- 🏢 **Azure Enterprise 통합 (Phase 3 & 4)**: Azure Document Intelligence (4.0 GA) 및 Azure Content Understanding을 통해 복잡한 PDF 레이아웃과 멀티미디어를 완벽히 구조화.
- 📦 **CLI 완벽 지원**: 옵시디언 없이도 언제 어디서나 독립적인 파이썬 CLI 환경에서 활용 가능.
- 🛡️ **철저한 보안**: API 키는 CLI 인자 대신 환경변수(`process.env`)로 주입되어 로그나 프로세스 모니터링 툴에 절대 노출되지 않음.
- 🌍 **다국어 및 타임존 지원**: `output_lang` 설정으로 8개 국어 지원, 현지 타임존(`timezone_offset`)에 맞춘 문서 메타데이터 자동 기입.
- 🗂️ **인라인 에셋 물리적 추출**: Markdown 내부에 숨어있는 Base64 이미지를 독립된 폴더로 물리적 추출 후 경로 자동 맵핑.

---

## 🛠️ 사용자 매뉴얼: 설치 및 사용법

### 1. Obsidian 플러그인으로 사용하기

**설치 방법:**
1. 이 레포지토리를 다운로드(Clone) 하거나 릴리즈된 `main.js`, `manifest.json`, `styles.css`, `engine/` 폴더를 복사합니다.
2. Obsidian 볼트 내 `<your-vault>/.obsidian/plugins/markitdown-flow/` 폴더를 생성하고 모든 파일을 넣습니다.
3. Obsidian 설정(Settings) ➔ **Community plugins** ➔ **MarkItDown Flow**를 활성화합니다.
4. 플러그인 설정 화면에서 `Python path`를 설정하고 필수 패키지(`markitdown`, `Pillow`, `geopy` 등)를 설치합니다.

**사용 방법:**
- **리본 아이콘 (Ribbon Icon)**: 클릭하여 원하는 파일 변환.
- **명령어 팔레트 (Command Palette)**: 
  - `Convert file to Markdown` (단일 파일 변환)
  - `Convert folder to Markdown` (폴더 전체 변환)
- **드래그 앤 드롭**: 이미지나 PDF 파일을 에디터로 드래그 앤 드롭 시 자동 변환되어 본문에 삽입됩니다!

---

### 2. CLI (독립형 Python 스크립트)로 사용하기

옵시디언을 켜지 않아도 터미널(CLI)에서 강력한 변환 엔진을 독립적으로 사용할 수 있습니다.

**필수 패키지 설치:**
```bash
cd engine/src
pip install markitdown Pillow geopy
# 옵션 (AI 사용 시)
pip install openai anthropic google-genai azure-ai-documentintelligence
```

**CLI 사용 예시:**
```bash
# 기본 파일 변환 (결과물은 출력 파일로 저장)
python markitdown_wrapper.py --input "sample.pdf" --output "result.md"

# 에셋(이미지 등)을 물리적 파일로 분리하여 추출
python markitdown_wrapper.py --input "sample.pdf" --output "result.md" --extract-assets --asset-dir "assets/"

# 추가 옵션 (JSON 형태로 전달)
python markitdown_wrapper.py --input "sample.png" --output "result.md" --plugin-args '{"output_lang": "ko", "exhaustive_mode": true}'
```

*(보안: `--plugin-args`에 API 키를 넣지 마세요! `DOCINTEL_CREDENTIAL`, `LLM_API_KEY` 환경변수를 설정하면 파이썬 엔진이 이를 감지하여 안전하게 동작합니다.)*

---

## ⚙️ 상세 옵션 (Plugin Args & Options)

설정 화면 또는 CLI `--plugin-args`를 통해 넘길 수 있는 핵심 옵션들입니다.

| 옵션명 | 타입 | 기본값 | 설명 |
|--------|------|--------|------|
| `output_lang` | string | `"en"` | 결과물 UI 언어 (지원: `ko`, `en`, `ja`, `zh`, `hi`, `fr`, `es`, `ar`) |
| `timezone_offset` | float | `null` | 메타데이터용 타임존 (예: 한국은 `9.0`). 미설정 시 시스템 로컬 타임 적용 |
| `exhaustive_mode` | boolean | `false` | 오프라인이 성공해도 AI, DocIntel 등 **모든 파이프라인을 강제 실행** |
| `extract_archives` | boolean | `false` | ZIP, TAR 압축 파일을 재귀적으로 해제하여 모두 마크다운으로 변환 |
| `enable_captions` | boolean | `false` | AI 프롬프트에 상세 캡션 생성 명령어를 자동으로 추가 |
| `max_recursion_depth` | int | `5` | 압축 파일 등 재귀 탐색 시 최대 깊이 제한 |
| `docintel_target_mimes` | list | `["application/pdf", ...]` | Azure DocIntel 처리 대상 MIME 타입 지정 |
| `ai_target_mimes` | list | `["image/", ...]` | LLM Vision AI 처리 대상 MIME 타입 지정 |
| `pdf_layout` | boolean | `true` | PDF 변환 시 레이아웃 형태 유지 (MarkItDown 코어 옵션) |

*(참고: 플러그인 UI에서는 AI 모델 API Key 및 Endpoint를 UI의 안전한 Password 필드로 입력받습니다.)*

---

## 🔒 보안 및 개인정보

**절대 API 키를 소스 코드나 깃허브에 하드코딩하지 마세요!**
MarkItDown Flow는 사용자의 API 키를 철저히 로컬(`data.json`)에만 보관하며, 서브프로세스를 호출할 때 **명령줄 인자(CLI Arguments)** 가 아닌 **운영체제 환경변수(Env Vars)** 로 전달하여 해커나 다른 프로세스 모니터링 툴에 의한 유출을 원천 차단합니다.

---

## 👨‍💻 개발 및 기여 (Development)

```bash
git clone https://github.com/greatgc-flow/MarkItDown-Flow.git
cd MarkItDown-Flow
npm install
npm run build
```

## 📜 라이선스 (License)

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 확인하세요.
이 프로젝트의 내부 코어 엔진은 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 라이브러리를 활용합니다.
