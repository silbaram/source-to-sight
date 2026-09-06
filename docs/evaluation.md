# 평가 실행 가이드

평가 도구는 소스에서 작성한 설명 후보를 고정 기준과 비교합니다. 현재 6개 공개 저장소·3개 언어·6유형의 동작 후보 24개와, 같은 대상의 규칙 후보 6개가 있습니다. 코드 위치·관계·필수 행동 주장과 경로·불확실성을 자동으로 검사하고, 문장의 사실성·규칙·이해도는 사람이 검토합니다. 규칙 평가는 원래 동작의 사실·근거가 보존되는지와 조건 비교 그림에 필요한 규칙이 있는지도 확인합니다.

## 저장된 사례 재현

[개발 환경](development.md)을 준비한 뒤 실행합니다.

~~~sh
npm run m1:sources
npm run eval:rules -- --output build/eval/m4
S2S_EVAL_DIR=build/eval/m4 npx playwright test tests/evaluation.spec.cjs tests/m2.spec.cjs tests/m3.spec.cjs tests/m4.spec.cjs
~~~

출력 디렉터리는 새 경로여야 합니다. 다시 실행할 때 `build/eval/m4-second`처럼 이름을 바꾸면 이전 결과와 답변이 보존됩니다. 저장소 소스는 실행하지 않으며 모델 API도 호출하지 않습니다. 고정된 소스를 읽어 현재 캔버스·규칙 템플릿으로 HTML을 만듭니다. M4도 M3에서 구성한 30개 분석 후보를 그대로 사용하며 재생·탐색 UI를 검증합니다. 동작 24개만 실행할 때는 `npm run eval:run -- --output <새 경로>`를 사용합니다.

| 출력 | 용도 |
| --- | --- |
| `<case-id>.html` | 실제 생성 화면. 예: `agent-parallel-tools.html`, `agent-parallel-tools-rules.html` |
| `<case-id>.render.json` | 소스 본문·앵커를 제거한 출력 데이터 |
| `results.json` / `report.md` | 유형별 점수·사례별 실패·누락·측정값·실행 조건 |
| `behavior-results.json` | M3 실행 중 보존한 기존 동작 24개 결과 |
| `<case-id>.review-template.json` | 답을 채우지 않은 사람 검토 양식 |

자동 통과와 최종 승인을 구분합니다. 검토가 없으면 `pending-review`이며 기본 종료 코드는 0입니다. `--strict`를 추가하면 선택한 전체 묶음(`eval:run`은 24개, `eval:rules`는 30개)이 자동 검사와 사람 검토를 모두 통과해야 0입니다. 일부 사례 실행은 전체 승인으로 처리하지 않습니다.

이전 18개만 재현할 때는 `--manifest eval/cases-m15.json`을 지정합니다. 해당 HTML의 공통 브라우저 검사는 `S2S_EVAL_MANIFEST=eval/cases-m15.json S2S_EVAL_DIR=<출력 경로> npx playwright test tests/evaluation.spec.cjs`로 실행합니다. M2 전용 검사는 복합 사례가 포함된 출력 경로를 사용합니다.

## 변경된 분석 결과 비교

새 후보는 [사례 목록](../eval/cases.md)의 질문·대상·포함/제외 범위·언어·프로파일·고정 커밋을 유지한 내부 IR로 준비합니다. 사례별 `<case-id>.json`을 한 디렉터리에 넣습니다. 표시 제목·라벨·노드 ID는 바꿀 수 있으며, 역할의 허용 코드 이름과 소스 위치는 각 사례의 정답 후보에 있습니다. 질문이나 범위를 바꾸면 같은 사례 비교로 인정하지 않습니다.

~~~sh
npm run eval:run -- --candidates build/my-candidates --output build/eval/changed
npm run eval:compare -- build/eval/m2/results.json build/eval/changed/results.json
~~~

저장된 기준 기록과 비교하려면 첫 경로에 `eval/runs/2026-09-06-baseline.json`을 사용합니다. 이는 사람 승인 전 임시 기준입니다. 정답 또는 소스 구성이 달라지면 비교 불가로 표시하며, `no-regression`도 사람 승인을 의미하지 않습니다. 필수 요소 누락, 새로운 오류, 치명적 오류, 기존 승인 상실은 개별 사례로 보고합니다.

18개에서 24개 또는 24개에서 30개로 확대한 결과를 비교할 때는 `--allow-suite-extension`을 명시합니다. 두 실행 모두 각 manifest의 전체 사례를 포함해야 하며 기존 사례의 정답·분류와 소스 목록은 같아야 합니다. 비교 결과에는 기존 비교 수와 추가 사례 목록이 나옵니다. 기존 누락과 신규 실패를 무시하는 옵션이 아닙니다.

~~~sh
npm run eval:compare -- eval/runs/2026-09-06-flow-animation.json build/eval/m2/results.json --allow-suite-extension
npm run eval:compare -- build/eval/m2/results.json build/eval/m3/results.json --allow-suite-extension
~~~

`eval:run`에서는 `--case utility-strip --case plugin-hooks`처럼 반복 지정해 일부만 실행할 수도 있습니다. 공통 지침 변경은 유형별 최소 1개와 과거 실패 사례, 특정 프로파일 변경은 해당 4개와 다른 유형 최소 3개, 공통 렌더러·스키마·검증기 변경은 `eval:rules`로 동작 24개와 규칙 6개를 모두 실행합니다. 도구가 변경 파일로 이 집합을 자동 선택하지는 않습니다.

M3의 [규칙 manifest](../eval/rules-cases.json)는 기존 동작 manifest와 별도로 후보·그림 구성·정답·짝 대상을 지정합니다. `--manifest`로 다른 규칙 manifest를 평가할 수 있지만 같은 여섯 프로파일과 동작 24개 구성을 유지해야 합니다. 규칙 후보 해시는 규칙 IR뿐 아니라 그림 구성과 원본 동작 해시도 포함합니다. 자동 비교는 규칙 ID나 문장 일치 대신 역할·소스 위치·상태·숫자 집합과 이유·예외의 존재를 검사합니다. 숫자가 맞아도 단위·조건·의미가 맞는지는 별도 검토가 필요합니다.

## 사람 검토 반영

[루브릭](../eval/rubric.md)에 따라 정답 후보와 실제 HTML을 소스와 대조합니다. 생성된 양식을 `build/reviews/<case-id>.json` 같은 별도 경로에 복사해 검토자·ISO 시각·각 판정을 채웁니다. `facts`와 `forbidden`의 번호는 정답 파일의 배열 순서이며, 금지 주장은 **없어야** pass입니다. 추가 노드·관계와 모든 본문·캡션도 검토합니다. 양식의 해시는 수정하지 않습니다.

~~~sh
npm run eval:run -- --reviews build/reviews --output build/eval/reviewed --strict
npm run eval:rules -- --reviews build/reviews --output build/eval/rules-reviewed --strict
~~~

후보·정답·두 스킬의 지침/렌더러/평가 코드/루브릭이 바뀌면 기존 답변은 오래된 검토로 판정합니다. M3는 그림 구성 또는 원본 동작만 바뀌어도 재검토합니다. 외부 동작 후보를 검토했다면 재실행에도 같은 `--candidates`를 지정합니다. 규칙 후보는 검토한 규칙 manifest를 유지합니다. 소스 위치가 맞다는 것만으로 문장·수치가 정확하다고 승인하지 않습니다.

## 사례 유지보수

`eval/m15/author_cases.py`는 기록된 12개 추가 분석을 재현하고 기존 M1 6개 분석을 복사하는 개발용 원장입니다. 새 저장소를 자동 탐색하지 않습니다. 원장이나 정답을 변경하기 전에 고정 소스를 다시 읽습니다. 원장을 재실행하면 후보의 생성 시각·해시가 바뀌며 재검토가 필요합니다. 기존 정답 파일은 자동 덮어쓰기하지 않으므로 정답 변경은 `expectations/`와 원장을 명시적으로 함께 편집합니다.

M2는 `eval/m2/author_cases.py`와 `reference_cases.py`를 사용합니다. 전자는 여섯 복합 후보와 전체 manifest를 재현하고, 후자는 별도로 작성한 정답 기준을 아직 파일이 없을 때만 기록합니다. 후보와 정답 양쪽의 범위·근거를 직접 확인해야 하며 자동으로 정답을 현재 후보에 맞추지 않습니다. 기존 M1.5 원장은 보존 manifest만 갱신해 24개 구성을 18개로 줄이지 않습니다.

M3는 `eval/m3/author_cases.py`로 같은 동작의 규칙 IR·그림 구성·별도로 기술한 규칙 기준을 기록합니다. 정답은 기존 파일을 보존하므로 변경하려면 원장과 JSON을 명시적으로 함께 수정합니다. [소스 재검토 기록](../eval/m3/discovery.md)에 실제로 읽은 범위와 제외한 내용을 남겼습니다. 소스 기반 계산 예시는 실행 관찰로 표기하지 않습니다.

평가 입력·출처·선택한 기준 기록은 `eval/`에서 관리하고, 매 실행의 HTML·전체 출력·임시 답변은 Git에서 제외되는 `build/`에 보관합니다. 생성 모델·토큰·비용·탐색 시간은 측정한 값이 없으면 null로 남습니다. 평가 실행 시간과 근거 줄 수를 생성 비용 또는 전체 소스 탐색량으로 해석하지 않습니다.
