# Source to Sight

[English](./README.md) | 한국어

복잡한 주제를 처음 보는 사람도 이해할 수 있는 시각적 결과물로 바꾸는 에이전트 스킬입니다.

범용 프로젝트 설명을 위한 고도화를 진행하고 있습니다. 현재 **M0 공통 데이터 모델·검증기·오프라인 워크플로 차트**를 구현했으며, 실제 플러그인 프레임워크·AI 에이전트·JavaScript 유틸리티를 포함한 11개 예시를 제공합니다. 저장소를 자동 탐색하는 `code-flow` 스킬은 다음 단계입니다.

[고도화 계획](plans/source-to-sight-evolution-plan.md) · [개발 및 예시 실행 방법](docs/development.md) · [예시의 출처와 검증 범위](fixtures/manifest.md)

`$visual-primer` 스킬은 실제 자료와 공식 출처를 확인한 뒤, 큰 그림과 적은 글로 설명하는 단일 HTML 페이지를 만듭니다. 결과물은 빌드 과정이나 별도 서버 없이 브라우저에서 바로 열 수 있습니다.

## 생성 결과

다음 한 줄로 OAuth 입문용 그림 설명서를 생성한 예시입니다.

```text
$visual-primer OAuth를 설명해줘
```

[![OAuth visual-primer 생성 결과 미리보기](./assets/oauth-visual-primer-example-preview.png)](./assets/oauth-visual-primer-example.html)

[OAuth visual-primer 예제 HTML 보기](./assets/oauth-visual-primer-example.html) · GitHub에서 실행 화면이 열리지 않으면 파일을 내려받아 브라우저로 여세요.

이 예시에는 다음 요소가 포함되어 있습니다.

- 의미에 따라 모양이 달라지는 연결선과 분명한 화살표
- Authorization Code + PKCE 데이터 흐름 애니메이션
- 단계별로 직접 진행할 수 있는 PKCE 시뮬레이션
- OAuth와 OpenID Connect의 차이를 보여주는 판단 구조
- 데스크톱과 모바일의 박스·레이어·오버플로 렌더링 QA

## 설치

Agent Skills CLI로 `visual-primer`를 설치합니다.

```bash
npx skills add silbaram/source-to-sight --skill visual-primer
```

설치 후 현재 세션에 스킬이 나타나지 않으면 새 대화를 시작하세요.

## 사용법

스킬 이름과 설명할 주제, 저장할 위치를 함께 적으면 됩니다.

```text
$visual-primer OAuth를 설명해줘. 결과를 docs/oauth-visual-primer-example.html에 저장해.
```

주제와 결과 위치를 자유롭게 바꿀 수 있습니다.

```text
$visual-primer 쿠버네티스의 Pod를 설명해줘. 결과는 현재 프로젝트 root에 생성해줘.
```

결과 파일은 다음 원칙을 따릅니다.

- 배경지식이 없다고 가정하고 실제 용어를 순서대로 소개합니다.
- 핵심 관계를 긴 글보다 큰 그림으로 먼저 보여줍니다.
- 연결선의 방향·모양·색을 관계의 의미에 맞게 구분합니다.
- 시간, 이동, 상태 변화가 중요한 경우에만 애니메이션이나 작은 시뮬레이션을 사용합니다.
- 공식 출처와 확인하지 못한 범위를 페이지 마지막에 기록합니다.
- UTF-8, 반응형 레이아웃, 키보드 포커스와 `prefers-reduced-motion`을 지원합니다.

## 업데이트

설치된 스킬은 다음 명령으로 업데이트합니다.

```bash
npx skills update visual-primer
```

현재 세션에 이전 버전이 남아 있으면 새 대화를 시작한 뒤 `$visual-primer`를 사용하세요.

## 저장소 구조

```text
.
├── README.md
├── README.ko.md
├── skills/visual-primer/
│   ├── SKILL.md
│   └── references/
│       ├── diagram-patterns.md
│       ├── qa.md
│       └── visual-treatment.md
└── assets/
    ├── oauth-visual-primer-example.html
    └── oauth-visual-primer-example-preview.png
```

- `SKILL.md`: `$visual-primer`가 설명을 조사하고 구성하는 핵심 규칙입니다.
- `references/`: 다이어그램, 디자인, 렌더링 QA 기준을 분리해 관리합니다.

이 저장소는 공개 [Agent Skills](https://agentskills.io/) 형식을 사용하며 [`skills` CLI](https://github.com/vercel-labs/skills)로 설치할 수 있습니다.
