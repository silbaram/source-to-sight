# Simple Output

복잡한 주제를 처음 보는 사람도 이해할 수 있는 시각적 결과물로 바꾸는 Codex 플러그인입니다.

현재 포함된 `$101-teacher` 스킬은 실제 자료와 공식 출처를 확인한 뒤, 큰 그림과 적은 글로 설명하는 단일 HTML 페이지를 만듭니다. 결과물은 빌드 과정이나 별도 서버 없이 브라우저에서 바로 열 수 있습니다.

## 생성 결과

다음 한 줄로 OAuth 입문용 그림 설명서를 생성한 예시입니다.

```text
$101-teacher OAuth를 설명해줘
```

[![OAuth 101 생성 결과 미리보기](./assets/oauth-101-example-preview.png)](./assets/oauth-101-example.html)

[OAuth 101 예제 HTML 보기](./assets/oauth-101-example.html) · GitHub에서 실행 화면이 열리지 않으면 파일을 내려받아 브라우저로 여세요.

이 예시에는 다음 요소가 포함되어 있습니다.

- 의미에 따라 모양이 달라지는 연결선과 분명한 화살표
- Authorization Code + PKCE 데이터 흐름 애니메이션
- 단계별로 직접 진행할 수 있는 PKCE 시뮬레이션
- OAuth와 OpenID Connect의 차이를 보여주는 판단 구조
- 데스크톱과 모바일의 박스·레이어·오버플로 렌더링 QA

## 설치

먼저 이 저장소를 Codex 마켓플레이스로 등록합니다.

```bash
codex plugin marketplace add silbaram/skill-plugin --ref main
```

마켓플레이스에서 `simple-output`을 설치합니다.

```bash
codex plugin add simple-output@personal
```

설치가 끝나면 새 대화를 시작하세요. 새 대화부터 플러그인의 스킬이 로드됩니다.

## 사용법

스킬 이름과 설명할 주제, 저장할 위치를 함께 적으면 됩니다.

```text
$101-teacher OAuth를 설명해줘. 결과를 docs/oauth-101-example.html에 저장해.
```

주제와 결과 위치를 자유롭게 바꿀 수 있습니다.

```text
$101-teacher 쿠버네티스의 Pod를 설명해줘. 결과는 현재 프로젝트 root에 생성해줘.
```

결과 파일은 다음 원칙을 따릅니다.

- 배경지식이 없다고 가정하고 실제 용어를 순서대로 소개합니다.
- 핵심 관계를 긴 글보다 큰 그림으로 먼저 보여줍니다.
- 연결선의 방향·모양·색을 관계의 의미에 맞게 구분합니다.
- 시간, 이동, 상태 변화가 중요한 경우에만 애니메이션이나 작은 시뮬레이션을 사용합니다.
- 공식 출처와 확인하지 못한 범위를 페이지 마지막에 기록합니다.
- UTF-8, 반응형 레이아웃, 키보드 포커스와 `prefers-reduced-motion`을 지원합니다.

## 업데이트

등록된 Git 마켓플레이스를 최신 상태로 갱신하고 플러그인을 다시 설치합니다.

```bash
codex plugin marketplace upgrade personal
codex plugin add simple-output@personal
```

업데이트 후에는 새 대화에서 `$101-teacher`를 다시 사용하세요.

## 저장소 구조

```text
.
├── .agents/plugins/marketplace.json
├── README.md
├── plugins/simple-output/
│   ├── .codex-plugin/plugin.json
│   └── skills/101-teacher/
│       ├── SKILL.md
│       └── references/
│           ├── diagram-patterns.md
│           ├── qa.md
│           └── visual-treatment.md
└── assets/
    ├── oauth-101-example.html
    └── oauth-101-example-preview.png
```

- `.agents/plugins/marketplace.json`: 설치 가능한 플러그인과 로컬 경로를 선언합니다.
- `.codex-plugin/plugin.json`: `simple-output`의 이름, 버전, 표시 정보와 스킬 경로를 정의합니다.
- `SKILL.md`: `$101-teacher`가 설명을 조사하고 구성하는 핵심 규칙입니다.
- `references/`: 다이어그램, 디자인, 렌더링 QA 기준을 분리해 관리합니다.

Codex 플러그인은 재사용 가능한 스킬과 외부 서비스 연결을 묶어 ChatGPT와 Codex를 확장하는 구조입니다. 개념과 구성 요소는 [공식 OpenAI Plugins 문서](https://developers.openai.com/plugins)를 참고하세요.
