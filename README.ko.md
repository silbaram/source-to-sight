# Source to Sight

Source to Sight는 소스 코드를 오프라인 시각적 설명으로 바꾸는 Agent Skills 패키지입니다. 유틸리티·라이브러리·프레임워크·AI 에이전트·이벤트 시스템·웹 프로젝트에 프로젝트 지도(`codebase-atlas`), 동작 설명(`code-flow`), 규칙 설명(`visual-primer`)을 공통으로 적용합니다.

## 설치

처음 사용한다면 [단계별 퀵스타터](docs/quickstart.md)를 따라 도구 확인 → 설치 → 요청 복사 → 첫 HTML 열기까지 진행하세요. 단계별 완료 기준과 문제 해결도 포함하며, [English guide](docs/quickstart.en.md)도 제공합니다.

설치에는 Git과 npm/npx를 포함한 Node.js 22.20.0 이상이 필요합니다([현재 Skills CLI 요구사항](https://github.com/vercel-labs/skills/blob/main/package.json)).

```text
npx skills add silbaram/source-to-sight --global --skill '*'
```

위 명령은 모든 스킬을 여러 프로젝트에서 사용할 수 있도록 설치합니다. 필요한 스킬만 설치하려면 `--skill '*'`를 `--skill code-flow`처럼 원하는 이름으로 바꿉니다. 각 스킬은 참고자료·템플릿·벤더 파일·라이선스를 포함한 디렉터리 전체를 설치해야 합니다.

소스 기반 생성에는 Python 3.10 이상이 필요합니다. 검증기가 포함되어 있어 별도의 Python 패키지 설치나 가상환경 준비는 필요하지 않습니다.

## 사용

```text
$code-flow 이 프로젝트의 요청 생명주기를 설명해줘.
$code-flow --explain 이 동작의 재시도와 실패 규칙을 설명해줘.
$codebase-atlas 이 프로젝트의 목적·책임·대표 기능을 설명해줘.
$visual-primer OAuth를 설명해줘.
```

**프로젝트 맵 → 기능·상세 흐름 → 핵심 비즈니스 로직의 그림 설명**으로 탐색합니다. 마지막 페이지는 [OAuth 예시](assets/oauth-visual-primer-example.html)처럼 주제에 맞는 큰 그림과 의미 있는 인터랙션으로 설명하며, 고정 흐름도나 규칙 카드만으로 제한하지 않습니다.

호스트 에이전트가 실제 소스를 읽고 근거와 시각적 설명을 작성하면, 생성 도구가 근거 위치·대상·페이지 연결을 확인해 오프라인 HTML로 묶습니다. 지도·동작은 공통 캔버스를 사용하고, 비즈니스 로직은 공통 탐색·근거 화면 안에 맞춤형 그림을 구성합니다. 별도 서버는 필요하지 않습니다. 필요한 상세만 요청하며, 미생성 항목의 버튼은 분석을 실행하지 않고 요청을 복사합니다.

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
