# 배포 가이드 (터미널 없이 웹 화면만으로 진행)

> 아래는 전부 웹 브라우저 클릭만으로 진행됩니다. 터미널/명령어는 필요 없습니다.

---

## 1단계. GitHub 계정 준비

1. https://github.com 접속 → 계정이 없으면 우측 상단 "Sign up"으로 가입 (이메일만 있으면 됨)
2. 이미 계정이 있으면 로그인

---

## 2단계. 새 저장소(repository) 만들기

1. 로그인 후 우측 상단 **"+"** 버튼 클릭 → **"New repository"** 클릭
2. Repository name: `hbm-report-app` (원하는 이름으로 자유롭게)
3. **Private** 선택 (외부 공개 원치 않으므로 반드시 Private로)
4. 다른 옵션은 그대로 두고 **"Create repository"** 클릭

---

## 3단계. 파일 업로드 (⚠️ 가장 실수하기 쉬운 단계)

**절대 원칙: `streamlit_app`이라는 이름의 폴더 자체가 저장소에 보이면 안 됩니다.** 저장소를 열었을 때 `app.py`, `config.py`가 폴더 없이 바로 최상위에 보여야 정상입니다.

1. 컴퓨터에서 다운로드한 zip 파일의 압축을 풉니다. `streamlit_app`이라는 폴더가 하나 생깁니다.
2. **그 `streamlit_app` 폴더를 더블클릭해서 안으로 들어갑니다.** (폴더를 열어서 안의 내용물이 보이는 상태여야 합니다)
3. 폴더 안에서 **전체 선택**(Windows: Ctrl+A, Mac: Cmd+A)을 합니다. 아래 8개 항목이 전부 파란색으로 선택되어야 합니다:
   - `assets` (폴더)
   - `core` (폴더)
   - `guide` (폴더)
   - `prompts` (폴더)
   - `DEPLOY.md`
   - `app.py`
   - `config.py`
   - `requirements.txt`
4. 저장소 화면에서 "uploading an existing file" 클릭
5. **선택된 8개 항목을 통째로** 끌어다 놓습니다. (바깥의 `streamlit_app` 폴더 이름표가 함께 딸려가지 않도록, 반드시 폴더 "안"에서 선택한 상태로 끌어야 합니다)
6. "Commit changes" 클릭

**업로드 직후 반드시 확인**: 저장소 메인 화면에 `streamlit_app`이라는 폴더가 **보이지 않고**, 대신 `assets`, `core`, `guide`, `prompts`, `app.py`, `config.py`, `requirements.txt`가 **각각 개별 항목으로 최상위에** 바로 보여야 합니다. 만약 `streamlit_app` 폴더가 하나 더 보인다면 잘못 업로드된 것이니, 그 폴더를 삭제하고 2~3단계를 다시 시도하세요.

---

## 4단계. Streamlit Community Cloud 연결

1. https://share.streamlit.io 접속
2. **"Sign in with GitHub"**로 로그인 (2단계에서 쓴 GitHub 계정과 동일하게)
3. **"Create app"** 또는 **"New app"** 클릭
4. 아래 항목 입력:
   - Repository: 방금 만든 `hbm-report-app` 선택
   - Branch: `main`
   - Main file path: `app.py`
5. **"Advanced settings"** 클릭 → **Secrets** 입력란에 아래 형식으로 입력:
   ```
   OPENAI_API_KEY = "여기에_실제_API_키_붙여넣기"
   OPENAI_MODEL = "gpt-5"
   OPENAI_FALLBACK_MODEL = ""
   ```
   (`OPENAI_FALLBACK_MODEL`은 기본 모델이 일시적으로 과부하일 때 사용할 대체 모델명을 넣는 선택 설정입니다.)
6. **"Deploy"** 클릭

---

## 5단계. 배포 확인

- 몇 분 정도 빌드 시간이 걸립니다. 화면에 로그가 실시간으로 나타납니다.
- 빌드 완료 후 앱 화면에 노란색 "MOCK 모드" 경고가 **뜨지 않아야** 정상입니다.
  (경고가 뜬다면 → Secrets에 키가 잘못 입력됐다는 뜻이니 4단계-5번을 다시 확인)
- 기술명에 아무거나 입력 → "다음 단계" → 시나리오/분류가 그럴듯하게 나오는지 확인
- "보고서 본문 생성 시작" 클릭 → 실제로 OpenAI API가 호출되며 몇 초~수십 초 소요될 수 있음
- 마지막에 "Word 문서 다운로드" 버튼으로 실제 파일이 받아지는지 확인

---

## 문제 발생 시 확인할 곳

Streamlit Cloud 앱 화면 우측 하단 **"Manage app"** 버튼을 누르면 실행 로그(에러 메시지)를 볼 수 있습니다. 에러 메시지를 캡처해서 알려주시면 원인을 같이 찾아보겠습니다.

**자주 발생할 수 있는 문제 (미리 알아두면 좋음)**
| 증상 | 예상 원인 |
|---|---|
| MOCK 모드 경고가 계속 뜸 | Secrets에 `OPENAI_API_KEY` 키 이름이 정확히 일치하지 않음 |
| "모듈을 찾을 수 없음" 에러 | 폴더 구조가 업로드 중 깨졌을 가능성 (3단계 확인) |
| 폰트 관련 에러 | `assets/fonts/NotoSansKR-subset.otf` 파일이 정상 업로드됐는지 확인 |
| Call 응답이 JSON 파싱 에러 | 실제 API가 프롬프트 스키마를 완벽히 지키지 않은 경우 — 아직 실제 검증이 안 된 부분이라 실제로 발생 가능성이 있음 |

---

## 무료 기반 특허/시장 검증 방식

이 앱은 KIPRISPlus 같은 유료/저한도 API가 없어도 동작하도록 설계되어 있습니다.

- 특허명세서 또는 기술문서를 업로드하면 AI가 기술 키워드와 검색식을 생성합니다.
- 보고서에는 KIPRIS, Google Patents, Espacenet, The Lens 검증 링크가 포함됩니다.
- 실제 검색결과 파일이 없으면 특허 정량값은 `D: 검증 전 후보 분석`으로 표시됩니다.
- 추후 담당자가 검색결과 CSV/Excel을 업로드하면 해당 분석은 `A: 실제 데이터 직접 집계`로 상향할 수 있습니다.
- 시장규모는 무료 공개자료 기준으로 출처별 후보값/범위/검증 필요성을 함께 표시합니다.
