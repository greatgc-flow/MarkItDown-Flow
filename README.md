# 🌟 MarkItDown Flow (Enterprise Edition)

![MarkItDown Flow Banner](https://img.shields.io/badge/MarkItDown-Flow-blue?style=for-the-badge&logo=markdown)
![Obsidian](https://img.shields.io/badge/Obsidian-Plugin-7A3CEF?style=for-the-badge&logo=obsidian)
![Python](https://img.shields.io/badge/Python-3.10%2B-FFD43B?style=for-the-badge&logo=python)

**MarkItDown Flow** is a powerful unified engine and Obsidian plugin that flawlessly converts data of any format—images, PDFs, audio, video, and archives (ZIP)—into pristine Markdown.

Going beyond simple text extraction, it guarantees zero-loss Markdown conversion through a **4-Phase Intelligent Fallback Pipeline** (Offline OCR ➔ AI Vision ➔ Azure DocIntel ➔ Azure Content Understanding).

---

## ✨ Key Features

- 📴 **Robust Offline Engine (Phase 1)**: Fast and cost-free offline text extraction utilizing ensemble OCR such as Tesseract and EasyOCR.
- 🤖 **Smart AI Vision Fallback (Phase 2)**: Automatically routes to **OpenAI (GPT-4o), Anthropic (Claude), and Google (Gemini)** vision models when offline extraction fails or encounters complex images.
- 🏢 **Azure Enterprise Integration (Phase 3 & 4)**: Perfectly structures complex PDF layouts and multimedia via Azure Document Intelligence (4.0 GA) and Azure Content Understanding.
- 📦 **Full CLI Support**: Can be used independently as a Python CLI environment anywhere, even without Obsidian.
- 🛡️ **Ironclad Security**: API keys are injected via environment variables (`process.env`) rather than CLI arguments, ensuring they are never exposed to logs or process monitoring tools.
- 🌍 **Multilingual & Timezone Support**: Supports 8 languages via the `output_lang` setting and automatically records document metadata aligned to your local timezone (`timezone_offset`).
- 🗂️ **Physical Inline Asset Extraction**: Physically extracts Base64 images hidden inside Markdown into an independent folder and maps the paths automatically.

---

## 🛠️ User Manual: Installation & Usage

### 1. Using as an Obsidian Plugin

**Installation:**
1. Clone this repository or download the released files: `main.js`, `manifest.json`, `styles.css`, and the `engine/` folder.
2. Create the `<your-vault>/.obsidian/plugins/markitdown-flow/` folder inside your Obsidian vault and place all files there.
3. In Obsidian, go to Settings ➔ **Community plugins** ➔ enable **MarkItDown Flow**.
4. In the plugin settings screen, set your `Python path` and install the required packages (`markitdown`, `Pillow`, `geopy`, etc.).

**Usage:**
- **Ribbon Icon**: Click to convert a desired file.
- **Command Palette**: 
  - `Convert file to Markdown` (Single file conversion)
  - `Convert folder to Markdown` (Convert an entire folder)
- **Drag & Drop**: Dragging and dropping an image or PDF file into the editor will automatically convert and insert it into your active note!

---

### 2. Using as a CLI (Standalone Python Script)

You can use the powerful conversion engine independently in your terminal (CLI) without opening Obsidian.

**Install Required Packages:**
```bash
cd engine/src
pip install markitdown Pillow geopy
# Optional (if using AI)
pip install openai anthropic google-genai azure-ai-documentintelligence
```

**CLI Usage Examples:**
```bash
# Basic file conversion (Output saved to a file)
python markitdown_wrapper.py --input "sample.pdf" --output "result.md"

# Extract assets (e.g., images) as physical files
python markitdown_wrapper.py --input "sample.pdf" --output "result.md" --extract-assets --asset-dir "assets/"

# Pass additional options (as a JSON string)
python markitdown_wrapper.py --input "sample.png" --output "result.md" --plugin-args '{"output_lang": "en", "exhaustive_mode": true}'
```

*(Security: Do NOT put API keys in `--plugin-args`! Set the `DOCINTEL_CREDENTIAL` and `LLM_API_KEY` environment variables; the Python engine will detect them and operate safely.)*

---

## ⚙️ Detailed Options (Plugin Args & Options)

These are the core options that can be passed via the settings screen or CLI `--plugin-args`.

| Option Name | Type | Default | Description |
|-------------|------|---------|-------------|
| `output_lang` | string | `"en"` | Output UI language (Supported: `en`, `ko`, `ja`, `zh`, `hi`, `fr`, `es`, `ar`) |
| `timezone_offset` | float | `null` | Timezone for metadata (e.g., `9.0` for Korea). Applies system local time if unset. |
| `exhaustive_mode` | boolean | `false` | **Forces execution of all pipelines** (AI, DocIntel, etc.) even if the offline phase succeeds. |
| `extract_archives` | boolean | `false` | Recursively extracts ZIP and TAR files, converting all contents to Markdown. |
| `enable_captions` | boolean | `false` | Automatically appends detailed caption generation instructions to AI prompts. |
| `max_recursion_depth` | int | `5` | Maximum depth limit for recursive extraction of archives. |
| `docintel_target_mimes` | list | `["application/pdf", ...]` | Target MIME types processed by Azure DocIntel. |
| `ai_target_mimes` | list | `["image/", ...]` | Target MIME types processed by LLM Vision AI. |
| `pdf_layout` | boolean | `true` | Preserves layout formatting during PDF conversion (MarkItDown core option). |

*(Note: In the plugin UI, AI model API Keys and Endpoints are securely collected via Password fields.)*

---

## 🔒 Security & Privacy

**NEVER hardcode API keys in the source code or GitHub!**
MarkItDown Flow keeps user API keys strictly local (`data.json`). When invoking the subprocess, it passes them via **Operating System Environment Variables (Env Vars)** instead of Command Line Arguments (CLI), structurally preventing leaks to hackers or process monitoring tools.

---

## 👨‍💻 Development & Contributing

```bash
git clone https://github.com/greatgc-flow/MarkItDown-Flow.git
cd MarkItDown-Flow
npm install
npm run build
```

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
The internal core engine of this project utilizes the [Microsoft MarkItDown](https://github.com/microsoft/markitdown) library.
