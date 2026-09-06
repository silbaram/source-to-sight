# M5 프로젝트 지도 소스 읽기 — 2026-09-07

기존 [고정 소스 목록](../m1/sources.json)의 여섯 저장소를 다시 읽어 프로젝트 목적·공개 기능·책임·관계를 작성했다. 새 저장소 자동 분석기나 대상 프로그램 실행 결과가 아니다. 호스트가 소스를 읽고 작성한 후보를 `author_cases.py`가 기록하며, `codebase-atlas`의 탐색 지침과 공통 작성·검증 도구로 조립한다. 독립 모델 생성, 대상 에이전트·모델 API 실행, 독립적인 사람 검토는 수행하지 않았다.

| 저장소 / 고정 커밋 | 읽은 주요 위치와 확인한 책임 | 지도 구성 / 남은 범위 |
| --- | --- | --- |
| strip-ansi / `38ff9f22` | package.json 배포 진입점·타입, index.js의 입력 검사와 정리 함수, index.d.ts 공개 선언, readme 목적 | 노드 1·구역 0·기능 2. 명시한 로컬 공개 기능 범위 complete. 외부 ansi-regex, 별도 CLI·스트림 저장소 제외 |
| pluggy / `4821148d` | pyproject.toml·공개 exports, _hooks.py의 표식·HookCaller, _manager.py의 등록·호출·모니터링, _callers.py의 multicall·기존 Result 처리 | 노드 6·구역 2·기능 3. 등록 책임과 호출/결과 책임을 구분. 외부 플러그인 업무 코드·배포 검색과 모든 호환성 경로 제외 |
| smolagents / `30bb1161` | 패키지·CLI 진입점, agents.py의 공통 반복·ToolCallingAgent·CodeAgent·실행기 선택·병렬 도구 처리, models.py·tools.py 인터페이스, memory.py·monitoring.py 기록 계약 | 노드 9·구역 3·기능 4. 두 실행 방식을 선택 관계로 표현. 모델 응답·외부 도구·원격 환경 내부, Gradio/MCP/웹 브라우저/직렬화 상세 제외 |
| golang-lru / `9c13c57d` | 루트·arc 모듈 선언, lru.go 공개 Cache와 Resize, 2q.go·arc/arc.go 정책, expirable/expirable_lru.go 초기화, simplelru/lru.go·internal/list.go 저장 구조 | 노드 6·구역 2·기능 3. expirable은 내부 목록에 직접 의존. 정책별 모든 퇴출 경로·동시 실행 결과·외부 콜백 내부 제외 |
| blinker / `c3364059` | pyproject.toml·공개 exports, base.py의 이름 공간·Signal 등록/전달·connected_to, _utilities.py의 식별자·약한 참조 | 노드 4·구역 1·기능 3. 사용자 수신자 경계와 순서 미정 유지. 수신자·변환기 구현 및 사용자가 바꾼 집합 순서 제외 |
| httprouter / `48401801` | go.mod, router.go의 Router·Handle·Params·표준 Handler 연결·ServeHTTP, tree.go 경로 등록/탐색, path.go CleanPath | 노드 5·구역 2·기능 3. 설정된 경로에서의 보정과 외부 처리기를 구분. 앱 처리기·HTTP 서버 내부·트리 최적화의 모든 경로 제외 |

총 31개 구성 요소, 책임 구역 10개, 대표 기능 18개다. 유틸리티 외 다섯 지도는 partial이며 모든 구현 경로를 추적했다고 표시하지 않는다. 각 후보의 `analysis.searched`, `subject.scope`, evidence 파일·줄·해시가 구체적인 범위를 기록한다. 근거가 같은 파일에 있다는 것만으로 모든 관계를 확인한 것으로 처리하지 않고 실제 호출·등록 위치를 함께 사용했다.

## 상세 설명 연결

각 지도 평가는 명시적으로 고른 한 개의 동작·규칙 쌍을 연결한다. 나머지 기능은 같은 평가 실행에서 이미 생성한 호환 페이지가 있으면 링크하고, 없으면 정확한 대상·포함/제외 범위·근거 위치를 담은 생성 요청으로 남긴다. 전체 카탈로그의 상세 설명을 선생성하지 않는다.

| 지도 | 연결을 검증하는 동작 |
| --- | --- |
| 유틸리티 | utility-strip + 입력 계약 규칙 |
| 프레임워크 | plugin-wrapper-unwind + 규칙 |
| 에이전트 | agent-parallel-tools + 규칙 |
| 라이브러리 | library-resize-callbacks + 규칙 |
| 이벤트 | event-async-lifecycle + 규칙 |
| 웹 | web-routing-fallbacks + 규칙 |

유틸리티 규칙은 기존 입력 검사의 사실을 유지하고 소스에서 읽은 이유·예외를 덧붙인 동반 설명이다. 지도 사례 안에서 검증하며 새로운 독립 생성 평가로 세지 않는다. 기존 24개 동작·6개 규칙 후보와 정답 파일은 보존한다. 기존 subject의 label-only target도 바꾸지 않고 지도에 별도의 코드 위치 근거를 추가한다.

## 정답 후보와 사람 검토

`reference_cases.py`에는 후보 노드 ID와 별도로 코드 이름·소스 역할·관계·구역 소속·기능 담당 역할을 명시했다. `expectations/`의 대상·범위·기능 ID는 최초 계약을 고정한 것이며, 재실행은 기존 파일을 덮어쓰지 않는다. 변경이 필요하면 소스를 확인하고 원장과 JSON을 명시적으로 함께 편집한다.

자동 검사는 역할/위치·관계·그룹 소속·기능 대상/범위/담당·독립 상태·양방향 링크를 확인한다. 목적 문장의 정확성, 책임 묶음의 적절성, 처음 보는 사람이 주요 부분과 대표 기능을 설명할 수 있는지는 생성된 해시 기반 검토 양식으로 사람이 확인해야 한다. 자동 통과만으로 `humanReviewed`를 변경하지 않는다.
