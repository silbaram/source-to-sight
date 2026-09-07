# Source to Sight

Source to Sight는 소스 코드를 오프라인 시각적 설명으로 바꾸는 Agent Skills 패키지입니다. 유틸리티·라이브러리·프레임워크·AI 에이전트·이벤트 시스템·웹 프로젝트에 프로젝트 지도(`codebase-atlas`), 동작 설명(`code-flow`), 규칙 설명(`visual-primer`)을 공통으로 적용합니다.

## 설치

```text
npx skills add silbaram/source-to-sight --skill code-flow
npx skills add silbaram/source-to-sight --skill visual-primer
npx skills add silbaram/source-to-sight --skill codebase-atlas
```

필요한 스킬만 설치할 수 있습니다. 각 스킬은 참고자료·템플릿·벤더 파일·라이선스를 포함한 디렉터리 전체를 설치해야 합니다.

## 사용

```text
$code-flow 이 프로젝트의 요청 생명주기를 설명해줘.
$code-flow --explain 이 동작의 재시도와 실패 규칙을 설명해줘.
$codebase-atlas 이 프로젝트의 목적·책임·대표 기능을 설명해줘.
$visual-primer OAuth를 설명해줘.
```

호스트 에이전트가 대상 소스를 읽고 근거를 기록하면, 스킬이 근거를 검증하고 브라우저에서 바로 열 수 있는 단일 HTML을 생성합니다. 생성 화면은 각 스킬의 유지되는 템플릿을 사용하며 별도 서버가 필요하지 않습니다.

## 저장소 구성

```text
skills/code-flow/       소스 기반 동작 설명과 공통 캔버스 렌더러
skills/visual-primer/   개념·소스 기반 규칙 설명
skills/codebase-atlas/  프로젝트 지도와 대표 기능 연결
docs/                   제품 안내와 배포 기준
assets/                 브라우저에서 열어 보는 시각화 예시
```

[문서 목록](docs/README.md)과 [배포 파일 기준](docs/distribution.md)을 확인하세요. 개발 평가 사례와 임시 UI 시안은 제품 브랜치에서 제거했으며, 필요할 때 별도 작업 공간에서 테스트 산출물을 생성합니다.

[English](README.md)
