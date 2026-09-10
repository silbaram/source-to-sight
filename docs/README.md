# Source to Sight 프로젝트 안내

처음 사용하는 분은 [한국어 퀵스타터](quickstart.md) 또는 [English quickstart](quickstart.en.md)부터 시작하세요. 입력할 장소, 복사할 요청, 단계별 완료 기준을 따라 첫 HTML을 만들 수 있습니다.

Source to Sight는 소프트웨어의 목적·구성·동작·규칙을 소스 근거와 함께 쉽게 설명하는 에이전트 스킬 모음입니다. 결과는 브라우저에서 열 수 있는 오프라인 HTML이며, 코드 본문 대신 설명·그림·근거 위치를 제공합니다.

현재 `code-flow`는 범위가 정해진 기능·공개 API·생명주기를 설명합니다. 유틸리티, 라이브러리, 프레임워크, AI 에이전트, 데이터/이벤트, 웹에 공통 모델과 화면을 사용합니다. 소스 탐색과 내용 검토는 호스트 에이전트가 수행하고, 도구는 근거 위치·해시·데이터 구조를 검증해 HTML을 생성합니다.

`visual-primer`는 개념과 소스 기반 규칙을 그림 중심으로 설명합니다. `$code-flow --explain`은 동작의 사실을 재사용해 핵심 비즈니스 로직을 주제별 그림과 필요한 인터랙션으로 설명하고, 정확한 조건·이유·예외·근거를 연결합니다. 기본 탐색 흐름은 **프로젝트 맵 → 기능·상세 흐름 → 핵심 비즈니스 로직의 그림 설명**이며, `codebase-atlas`가 필요한 페이지를 연결합니다.

동작 화면에서는 배속·단계 선택·키보드 탐색과 모바일 설명 패널 크기 조절을 사용할 수 있습니다. 현재 위치 링크를 복사하면 같은 HTML의 노드나 흐름 단계를 다시 열 수 있으며 자동재생은 시작하지 않습니다.

| 안내 | 내용 |
| --- | --- |
| [한국어 퀵스타터](quickstart.md) / [English quickstart](quickstart.en.md) | 도구·설치 확인, 복사 가능한 요청, 첫 결과 열기, 선택 기능, 공유·갱신·문제 해결 |
| [한국어 시작 안내](../README.ko.md) / [English](../README.md) | 설치, 스킬 사용, 실제 사례와 지원 범위 |
| [프로젝트 지도](project-maps.md) | 책임 구역, 기능 선택과 지도↔동작↔규칙 이동 |
| [유지보수 문서 시각 검증](../visual-checks/README.md) | 실제 프로젝트의 HTML 11개와 데스크톱·모바일 화면 캡처 |
| [배포 파일 기준](distribution.md) | 제품 스킬·안내와 개발·검증 보관물의 구분 |
| [code-flow](../skills/code-flow/SKILL.md) | 동작 설명 스킬의 입력·출력과 사용 계약 |
| [규칙 설명 생성](../skills/visual-primer/references/source-rules.md) | 소스 기반 맞춤형 그림 설명과 지도·동작 페이지 연결 |
| [맞춤형 그림 작성](../skills/visual-primer/references/authored-layout.md) | 버전 2 HTML/SVG·인터랙션 구성, 근거 연결과 검증 기준 |
| [렌더러 계약](../skills/code-flow/references/renderer-contract.md) | 데이터·근거·오프라인 화면의 동작 기준 |

이 디렉터리에는 제품 설명과 사용 안내를 관리합니다. 배포 경계와 보관 원칙은 [배포 파일 기준](distribution.md)에 정리되어 있습니다.
