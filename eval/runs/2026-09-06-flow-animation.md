# 2026-09-06 재생 연결 애니메이션 추가 후 회귀 평가

공통 템플릿에 연결선을 따라 이동하는 표시, 도착 강조, 출발·도착 이름, 연결 영역 맞춤을 추가하고 18개 후보를 재생성했습니다. [이전 패널 수정 기준](2026-09-06-panel-fix.md)과 비교 결과는 `no-regression`입니다. 소스 분석과 정답 후보는 같으며 렌더러 계약·엔진 해시가 바뀌었습니다. 사람 검토는 대기 중입니다.

`npm run eval:run -- --output build/eval/m15` 실행 결과를 [JSON](2026-09-06-flow-animation.json)으로 보존합니다. 현재 `build/eval/m15`에는 애니메이션이 포함된 HTML과 새 평가 기록·빈 검토 양식이 있으며, 직전 실행은 `build/eval/m15-before-flow-animation`에 보존했습니다. [화면·재생 검사](../reports/flow-animation-verification.md)는 별도 기록입니다.

## 실행 결과

- Run: `2026-09-06T12:08:25.688143+00:00`
- Mode: `recorded-candidate-replay`; this is candidate replay, not independent model generation.
- Gate: **pending-review**; coverage: 18/18
- Engine: `d66fc6b513966481304c64ea6b59cf381a2d7ac94cbee512ab588f9101cff163`; repository: `52b2235b9bde320e7e5e2786c54c4d06cc045fb9`; clean: `False`
- Unknown generation tokens, time, cost and model remain null. Evidence lines are not total discovery reads.
- Automatic checks verify explicit structure/location criteria. Human facts, conditions and comprehension require review.

| Profile | Cases | Automatic pass | Human accepted | Node recall | Edge recall | Critical findings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cli-utility | 3 | 3 | 0 | 100% | N/A | 0 |
| library-sdk | 3 | 3 | 0 | 100% | 100% | 0 |
| framework-plugin | 3 | 3 | 0 | 100% | 100% | 0 |
| ai-agent | 3 | 3 | 0 | 100% | 100% | 0 |
| data-event | 3 | 3 | 0 | 100% | 100% | 0 |
| web | 3 | 3 | 0 | 100% | 100% | 0 |

| Case | Auto | Final | Analysis | Evidence files/lines | Review | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| utility-strip | passed | pending-review | complete | 1/15 | pending | — |
| plugin-hooks | passed | pending-review | partial | 3/140 | pending | — |
| agent-tool-loop | passed | pending-review | partial | 1/311 | pending | — |
| library-eviction | passed | pending-review | partial | 2/63 | pending | — |
| web-dispatch | passed | pending-review | partial | 2/179 | pending | — |
| event-receivers | passed | pending-review | partial | 1/136 | pending | — |
| utility-invalid-input | passed | pending-review | complete | 1/15 | pending | — |
| utility-plain-text | passed | pending-review | complete | 1/15 | pending | — |
| plugin-blocked-registration | passed | pending-review | complete | 1/85 | pending | — |
| plugin-unblock | passed | pending-review | complete | 1/9 | pending | — |
| library-invalid-capacity | passed | pending-review | complete | 1/13 | pending | — |
| library-peek | passed | pending-review | complete | 2/16 | pending | — |
| web-invalid-registration | passed | pending-review | complete | 1/45 | pending | — |
| web-lookup | passed | pending-review | complete | 2/120 | pending | — |
| agent-unknown-tool | passed | pending-review | complete | 1/36 | pending | — |
| agent-max-steps | passed | pending-review | partial | 1/131 | pending | — |
| event-muted | passed | pending-review | complete | 1/61 | pending | — |
| event-receiver-check | passed | pending-review | complete | 1/20 | pending | — |
