# MarkItDown-Flow: 구조적 TDD(테스트 주도 개발) 구현 계획서

본 문서는 새롭게 편성된 MECE 기반 아키텍처(Engine / Plugin 분리) 위에서 향후 개발될 기능들을 안전하고 체계적으로 구현하기 위한 구조적 TDD 진행 계획입니다.

## 🎯 TDD 핵심 원칙
1. **Red (실패하는 테스트 작성)**: 구현 전, 요구사항을 명세하는 테스트부터 작성 (결과는 Fail).
2. **Green (테스트 통과)**: 에러가 나지 않도록 최소한의 하드코딩 또는 실제 로직을 작성.
3. **Refactor (리팩토링)**: 하드코딩을 제거하고 일반화/패턴 적용, 코드 품질 개선.
4. **Mocking 필수**: LLM, Azure Doc Intel 등 과금이 발생하는 외부 API는 TDD 과정에서 100% Mock(가짜 객체)으로 대체하여 비용을 차단.

---

## 🏗️ 1단계: Python Engine - 오프라인 이미지 라우터 (P0)

> **목표**: 비싼 AI 호출 이전에 오프라인 앙상블 OCR 및 분류(Deskew, Tesseract 등)를 먼저 거치도록 `SmartImageRouter` 구현.

### [RED] 테스트 시나리오 정의 (`test_image_router.py`)
- **T1 (Blank 감지)**: 평균 픽셀 값이 극단적인 빈 이미지 입력 시, AI 호출 없이 즉시 스킵(`status: skipped`) 반환.
- **T2 (Document 분류 및 Deskew)**: 텍스트 비중이 높은 이미지가 5도 이상 기울어져 있을 때, `skew_angle`을 계산하고 보정 로직을 호출하는지 확인.
- **T3 (OCR Ensemble)**: Tesseract 엔진이 신뢰도 80 이상을 반환하면, AI 에스컬레이션 플래그(`should_escalate_to_ai`)가 `False`로 떨어지는지 검증.
- **T4 (AI 에스컬레이션)**: 오프라인 엔진 신뢰도가 낮거나(70 미만), 자연 사진(Photo)으로 분류되면 `should_escalate_to_ai`가 `True`로 설정되는지 확인.

### [GREEN & REFACTOR] 구현 로직
- `engine/src/image_router.py`에 `ImageClassifier`, `ImagePreprocessor`, `OCREnsemble` 클래스 스켈레톤 추가.
- `pip install pytesseract opencv-python numpy` 등 의존성을 추가하되, **Lazy Import**를 적용하여 미설치 환경에서도 엔진이 죽지 않도록 방어 코드(try/except ImportError) 작성.

---

## 🛡️ 2단계: TypeScript Plugin - 보안 및 API 키 관리 (P1)

> **목표**: 하드코딩된 API 키를 플러그인 설정 UI로 완전히 빼내고, Python 런타임에 안전하게 전달(임시 환경변수 등)하는 구조 검증.

### [RED] 테스트 시나리오 정의 (`MarkitdownConverter.test.ts`)
- **T5 (키 유출 방지)**: `buildArgs` 함수가 반환하는 CLI 인자 배열(Array)에 API 키(ex: `sk-ant-xxx`)가 직접 노출되지 않는지(또는 안전하게 직렬화되어있는지) 검증.
- **T6 (동적 모델 파라미터)**: UI에서 Azure Doc Intel 엔드포인트를 입력하면 `--docintel-endpoint` 인자가 올바르게 매핑되는지 확인.
- **T7 (Missing Key 경고)**: 사용자가 AI 기능(LLM Vision)을 켰으나 API 키가 비어있을 때 변환 시도를 차단하고 적절한 에러(`ConversionResult.error`)를 반환하는지 테스트.

### [GREEN & REFACTOR] 구현 로직
- `plugin/src/settings/`에 API 키 입력 폼 렌더링.
- `ConversionService.ts`에서 Python Child Process를 생성할 때 `process.env`를 얕은 복사하여 API 키를 임시 주입하는 방식으로 통신 보안성 향상.

---

## 🤖 3단계: Python Engine - AI & Doc Intel Fallback (P2)

> **목표**: 1단계(Offline)에서 실패하여 에스컬레이션된 이미지나, 복잡한 문서(PDF 레이아웃)가 Azure Doc Intel과 LLM으로 올바르게 Fallback 되는지 검증.

### [RED] 테스트 시나리오 정의 (`test_ai_fallback.py`)
- **T8 (Doc Intel 라우팅)**: `application/pdf` MIME이 들어오고 `--docintel-endpoint`가 존재할 때, 내부적으로 Azure 클라이언트를 1회 호출(`call_count == 1`)하는지 검증 (Mock 사용).
- **T9 (LLM Vision Fallback)**: Doc Intel이 없거나 사진(Photo) 파일인 경우, `openai` 또는 `anthropic` 클라이언트를 1회 호출하는지 검증.
- **T10 (과금/API 한도 방지 - 429 에러)**: API가 429 Too Many Requests 에러를 던질 때 엔진이 죽지 않고, 우회(Failover) 로직을 타거나 친절한 에러(`{"error": "API Rate Limit Exceeded"}`)를 반환하는지 검증.

### [GREEN & REFACTOR] 구현 로직
- `engine/src/markitdown_wrapper.py` 내의 `_run_ai()` 및 `_run_docintel()` 메서드를 리팩토링.
- API 호출 부를 별도 클래스(`AIAgent`)로 추상화하여, Gemini / Claude / GPT / Azure의 규격을 통일하고 Mocking하기 쉽게 의존성 역전(DIP) 패턴 적용.

---

## 🚀 4단계: E2E (End-to-End) 통합 검증

- **T11 (전체 파이프라인 관통)**: TS(옵시디언)에서 가짜 PDF 파일을 변환 요청 -> Python 서브프로세스 기동 -> Offline OCR 통과 -> 결과 JSON 리턴 -> TS에서 변환 완료(Notice) 알림까지의 전체 흐름 통합 테스트.
