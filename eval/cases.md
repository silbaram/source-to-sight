# 동작·규칙 설명 평가 사례 목록

공개 저장소 6개·언어 3개·유형별 4개, 총 24개입니다. M1.5의 기존 18개 입력을 보존하고 M2 복합 사례를 유형별 하나씩 추가했습니다. 모두 코딩 에이전트가 작성한 후보이며 **사람이 확정한 골든셋이나 독립적인 모델 생성 실험이 아닙니다.**

M3는 위 동작 24개를 보존하고 같은 대상의 규칙 설명 6개를 추가합니다. 통합 평가는 30개이며 원래 동작 manifest와 규칙 manifest를 분리해 이전 비교 기준을 유지합니다.

## 고정 소스

| 저장소 | 언어 | 고정 커밋 |
| --- | --- | --- |
| chalk/strip-ansi | JavaScript | [38ff9f2282540422031ed523f0060c7bb575e20f](https://github.com/chalk/strip-ansi/tree/38ff9f2282540422031ed523f0060c7bb575e20f) |
| pytest-dev/pluggy | Python | [4821148db2f4c6daa62ad8bdcae2918ecf27a731](https://github.com/pytest-dev/pluggy/tree/4821148db2f4c6daa62ad8bdcae2918ecf27a731) |
| huggingface/smolagents | Python | [30bb1161095dbae2271e6bc3cc4c219cc3897a57](https://github.com/huggingface/smolagents/tree/30bb1161095dbae2271e6bc3cc4c219cc3897a57) |
| hashicorp/golang-lru | Go | [9c13c57de0bedd6b3e21183b34072e417ffa69d1](https://github.com/hashicorp/golang-lru/tree/9c13c57de0bedd6b3e21183b34072e417ffa69d1) |
| julienschmidt/httprouter | Go | [484018016424d215c0b87c42f4c9b57d980fbd00](https://github.com/julienschmidt/httprouter/tree/484018016424d215c0b87c42f4c9b57d980fbd00) |
| pallets-eco/blinker | Python | [c3364059663df1ddce32799d6b1922af89a345f6](https://github.com/pallets-eco/blinker/tree/c3364059663df1ddce32799d6b1922af89a345f6) |

원본 출처와 커밋의 단일 manifest는 [m1/sources.json](m1/sources.json)입니다. `npm run m1:sources`로 같은 소스를 확보하며 각 저장소의 라이선스를 소스 체크아웃에서 보존합니다. 평가 도구는 대상 프로그램을 실행하지 않습니다.

## 사례

| 유형 | 변형 | 설명 질문 / 정답 후보 | 예상 상태 | 분석 IR |
| --- | --- | --- | --- | --- |
| ai-agent | 일반 | [ToolCallingAgent가 요청을 받아 도구를 사용하고 실행을 종료하는 흐름을 설명해 줘.](m15/expectations/agent-tool-loop.json) | partial | [agent-tool-loop](m15/graphs/agent-tool-loop.json) |
| ai-agent | 경계 | [등록되지 않은 도구 이름을 요청하면 무엇을 실행하나요?](m15/expectations/agent-unknown-tool.json) | complete | [agent-unknown-tool](m15/graphs/agent-unknown-tool.json) |
| ai-agent | 동적·부분 | [에이전트가 단계 한계까지 최종 답을 얻지 못하면 어떻게 마무리하나요?](m15/expectations/agent-max-steps.json) | partial | [agent-max-steps](m15/graphs/agent-max-steps.json) |
| cli-utility | 일반 | [stripAnsi는 문자열을 어떻게 검사하고 터미널 서식 표시를 제거하나요?](m15/expectations/utility-strip.json) | complete | [utility-strip](m15/graphs/utility-strip.json) |
| cli-utility | 경계 | [stripAnsi에 문자열이 아닌 값을 넘기면 어떻게 되나요?](m15/expectations/utility-invalid-input.json) | complete | [utility-invalid-input](m15/graphs/utility-invalid-input.json) |
| cli-utility | 최소 | [제어 표시가 없는 문자열도 치환하나요?](m15/expectations/utility-plain-text.json) | complete | [utility-plain-text](m15/graphs/utility-plain-text.json) |
| data-event | 일반 | [Blinker에서 수신자를 연결한 뒤 send하면 누가 호출되고 어떤 결과가 돌아오나요?](m15/expectations/event-receivers.json) | partial | [event-receivers](m15/graphs/event-receivers.json) |
| data-event | 경계 | [신호를 muted 문맥 안에서 보내면 수신자에게 나중에 전달되나요?](m15/expectations/event-muted.json) | complete | [event-muted](m15/graphs/event-muted.json) |
| data-event | 최소 | [has_receivers_for가 참이면 살아 있는 수신자의 호출이 보장되나요?](m15/expectations/event-receiver-check.json) | complete | [event-receiver-check](m15/graphs/event-receiver-check.json) |
| framework-plugin | 일반 | [pluggy에서 플러그인 등록과 이후 일반 훅 호출은 어떻게 연결되나요?](m15/expectations/plugin-hooks.json) | partial | [plugin-hooks](m15/graphs/plugin-hooks.json) |
| framework-plugin | 경계 | [차단한 플러그인 이름을 다시 등록하면 어떻게 되나요?](m15/expectations/plugin-blocked-registration.json) | complete | [plugin-blocked-registration](m15/graphs/plugin-blocked-registration.json) |
| framework-plugin | 최소 | [플러그인 이름의 차단을 해제하면 자동으로 다시 등록되나요?](m15/expectations/plugin-unblock.json) | complete | [plugin-unblock](m15/graphs/plugin-unblock.json) |
| library-sdk | 일반 | [Cache.Add는 용량이 찼을 때 무엇을 제거하고 사용자 콜백을 언제 호출하나요?](m15/expectations/library-eviction.json) | partial | [library-eviction](m15/graphs/library-eviction.json) |
| library-sdk | 경계 | [simplelru.NewLRU에 양수가 아닌 용량을 전달하면 어떻게 되나요?](m15/expectations/library-invalid-capacity.json) | complete | [library-invalid-capacity](m15/graphs/library-invalid-capacity.json) |
| library-sdk | 최소 | [Cache.Peek는 최근 사용 순서를 바꾸나요?](m15/expectations/library-peek.json) | complete | [library-peek](m15/graphs/library-peek.json) |
| web | 일반 | [httprouter에 등록한 경로가 일치할 때 요청은 어떤 핸들러로 전달되나요?](m15/expectations/web-dispatch.json) | partial | [web-dispatch](m15/graphs/web-dispatch.json) |
| web | 경계 | [Router.Handle은 어떤 잘못된 등록 입력을 즉시 거부하나요?](m15/expectations/web-invalid-registration.json) | complete | [web-invalid-registration](m15/graphs/web-invalid-registration.json) |
| web | 최소 | [Router.Lookup은 찾은 핸들러를 실행하거나 리다이렉트하나요?](m15/expectations/web-lookup.json) | complete | [web-lookup](m15/graphs/web-lookup.json) |

## 검토 기준과 출처 기록

M2의 복합 사례는 아래와 같습니다. 같은 저장소 안에서도 실제 설명 대상에 따라 프로파일을 고릅니다. 예를 들어 smolagents의 `Retrying`은 모델과 무관한 함수 재시도 유틸리티이며, `ApiModel`의 호출 정책 설정을 함께 읽습니다.

| 유형 | 설명 질문 / 정답 후보 | 분석 IR |
| --- | --- | --- |
| cli-utility | [실패한 함수를 언제 다시 호출하고 중단하는가](m2/expectations/utility-retry-budget.json) | [utility-retry-budget](m2/graphs/utility-retry-budget.json) |
| framework-plugin | [첫 결과와 오류가 래퍼를 거쳐 어떻게 반환되는가](m2/expectations/plugin-wrapper-unwind.json) | [plugin-wrapper-unwind](m2/graphs/plugin-wrapper-unwind.json) |
| library-sdk | [캐시 축소의 제거 반복과 콜백·잠금 경계](m2/expectations/library-resize-callbacks.json) | [library-resize-callbacks](m2/graphs/library-resize-callbacks.json) |
| ai-agent | [병렬 도구의 제출·수집·기록과 다음 단계의 판단](m2/expectations/agent-parallel-tools.json) | [agent-parallel-tools](m2/graphs/agent-parallel-tools.json) |
| data-event | [비동기 전달과 임시 수신자의 실패·해제 경계](m2/expectations/event-async-lifecycle.json) | [event-async-lifecycle](m2/graphs/event-async-lifecycle.json) |
| web | [경로 불일치 시 리다이렉트·OPTIONS·405·404 선택](m2/expectations/web-routing-fallbacks.json) | [web-routing-fallbacks](m2/graphs/web-routing-fallbacks.json) |

여섯 복합 사례는 외부 구현 또는 동적 결과를 남긴 `partial` 후보입니다. 전체 예상 상태는 `complete` 12개 / `partial` 12개입니다. [M2 소스 읽기 기록](m2/discovery.md)은 범위·근거와 확인한 한계를 설명합니다. [전체 manifest](cases.json)는 24개이며 [M1.5 manifest](cases-m15.json)는 기존 18개 구성을 그대로 보존합니다.

각 정답 후보에는 고정 질문·범위, 필수 역할과 소스 위치, 관계의 방향·종류·확신 수준, 빠지면 안 되는 사실, 금지할 주장, 명시적 금지 관계, 순서 없는 설명 여부가 있습니다. 역할·관계 기준은 작성자가 소스를 읽어 별도로 기록했으며 후보 IR의 ID에서 자동 추출한 정답이 아닙니다. 같은 작성자가 분석과 정답 후보를 작성했으므로 독립 검토가 필요합니다.

추가 분석은 `index.js`의 입력 검사·빠른 반환, pluggy `_manager.py`의 차단·해제, simplelru 생성자와 공개/내부 Peek, httprouter Handle·Lookup과 트리 조회, smolagents 도구 이름 검사·단계 한계·최종 답변 함수, Blinker muted·send·has_receivers_for를 읽었습니다. 각 IR의 `analysis.searched`는 기록된 탐색 파일이며 전체 읽기 횟수·시간을 측정한 값은 아닙니다. 실제 근거의 줄·해시는 IR에, 비교할 대표 위치는 정답 후보에 있습니다.

작은 사례는 한 노드와 재생 없는 구성이 정상입니다. 차단/등록, muted/send처럼 호출자가 각각 사용하는 진입점에는 존재하지 않는 자동 호출을 추가하지 않습니다. 최대 단계 사례는 양수 단계 한계로 범위를 제한하며 실제 모델 답변은 미해소로 유지합니다.

## M3 짝 규칙 설명

| 유형 | 규칙 후보 | 그림에서 비교·설명하는 내용 |
| --- | --- | --- |
| cli-utility | [utility-retry-budget-rules](m3/graphs/utility-retry-budget-rules.json) | 기본 총 시도와 호출 정책, 재시도 중단, 대기 갱신 |
| framework-plugin | [plugin-wrapper-unwind-rules](m3/graphs/plugin-wrapper-unwind-rules.json) | 첫 유효 결과와 None, 래퍼의 역순 복귀와 결과 변경 |
| library-sdk | [library-resize-callbacks-rules](m3/graphs/library-resize-callbacks-rules.json) | 용량 축소/확대의 계산 예시, 기록 시점과 콜백 실패 |
| ai-agent | [agent-parallel-tools-rules](m3/graphs/agent-parallel-tools-rules.json) | 호출별/기본 한계, 계속 가능한 오류/생성 오류, 완료와 기록 순서 |
| data-event | [event-async-lifecycle-rules](m3/graphs/event-async-lifecycle-rules.json) | 비동기/동기 수신자, 실패 후 전달, 임시 등록과 해제 |
| web | [web-routing-fallbacks-rules](m3/graphs/web-routing-fallbacks-rules.json) | 405/자동 OPTIONS, 경로 보정, 기본 404 |

[규칙 manifest](rules-cases.json), [그림 구성](m3/layouts/), [정답 후보](m3/expectations/)와 [소스 읽기 기록](m3/discovery.md)을 함께 관리합니다. 규칙 27개는 기존 동작의 사실·범위·근거를 유지하며 이유와 예외를 보완한 것입니다. 여섯 결과는 동적·외부 구현의 한계를 유지한 `partial`이며, 통합 예상 상태는 complete 12 / partial 18입니다. 유틸리티와 에이전트는 같은 저장소의 서로 다른 책임을 설명합니다.

실행과 검토 반영은 [평가 가이드](../docs/evaluation.md), 채점과 게이트는 [루브릭](rubric.md), 보존한 실행 결과는 [실행 기록](runs/)을 확인합니다. 생성 HTML은 `build/eval/<run>/`에 있습니다. 동작에는 [공통 캔버스 템플릿](../skills/code-flow/templates/flow-viewer-template.html), 소스 기반 규칙에는 [primer 템플릿](../skills/visual-primer/templates/rules-template.html)을 사용합니다.
