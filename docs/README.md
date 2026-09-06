# Source to Sight 프로젝트 안내

Source to Sight는 소프트웨어의 목적·구성·동작·규칙을 소스 근거와 함께 쉽게 설명하는 에이전트 스킬 모음입니다. 결과는 브라우저에서 열 수 있는 오프라인 HTML이며, 코드 본문 대신 설명·그림·근거 위치를 제공합니다.

현재 `code-flow`는 범위가 정해진 기능·공개 API·생명주기를 설명합니다. 유틸리티, 라이브러리, 프레임워크, AI 에이전트, 데이터/이벤트, 웹에 공통 모델과 화면을 사용합니다. 소스 탐색과 내용 검토는 호스트 에이전트가 수행하고, 도구는 근거 위치·해시·데이터 구조를 검증해 HTML을 생성합니다.

`visual-primer`는 개념 설명을 제공합니다. 저장소의 규칙을 함께 탐색하는 전체 연계는 M3, `codebase-atlas`의 프로젝트 전체 탐색은 M5 개발 범위입니다.

| 안내 | 내용 |
| --- | --- |
| [한국어 시작 안내](../README.ko.md) / [English](../README.md) | 설치, 스킬 사용, 실제 사례와 지원 범위 |
| [개발 가이드](development.md) | 개발 환경, 예제 재현, 템플릿 변경과 검사 방법 |
| [평가 가이드](evaluation.md) | 18개 사례 실행·결과 비교·사람 검토 반영 |
| [code-flow](../skills/code-flow/SKILL.md) | 동작 설명 스킬의 입력·출력과 사용 계약 |
| [렌더러 계약](../skills/code-flow/references/renderer-contract.md) | 데이터·근거·오프라인 화면의 동작 기준 |

이 디렉터리에는 프로젝트 설명과 사용·개발 가이드를 관리합니다. 개발계획과 UI 설계는 [plans](../plans/), 평가 사례는 [eval/cases.md](../eval/cases.md), 검증·리뷰·사람 검토 기록과 보존한 스크린샷은 [eval/reports](../eval/reports/)에 있습니다.
