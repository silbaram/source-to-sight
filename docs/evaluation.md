# 평가 실행 가이드

평가 도구는 소스에서 작성한 설명 후보를 고정 기준과 비교합니다. 현재 6개 공개 저장소·3개 언어·6유형에 일반/경계/최소 또는 동적 사례를 각각 배치한 18개 후보가 있습니다. 코드 위치·관계·불확실성을 자동으로 검사하고, 사실·규칙·이해도는 사람이 검토합니다.

## 저장된 사례 재현

[개발 환경](development.md)을 준비한 뒤 실행합니다.

~~~sh
npm run m1:sources
npm run eval:run -- --output build/eval/m15
S2S_EVAL_DIR=build/eval/m15 npx playwright test tests/m15.spec.cjs
~~~

출력 디렉터리는 새 경로여야 합니다. 다시 실행할 때 `build/eval/m15-second`처럼 이름을 바꾸면 이전 결과와 답변이 보존됩니다. 저장소 소스는 실행하지 않으며 모델 API도 호출하지 않습니다. 고정된 소스를 읽어 현재 공통 템플릿으로 HTML을 만듭니다.

| 출력 | 용도 |
| --- | --- |
| `<case-id>.html` | 실제 생성 화면. 예: `agent-max-steps.html`, `library-peek.html` |
| `<case-id>.render.json` | 소스 본문·앵커를 제거한 출력 데이터 |
| `results.json` / `report.md` | 유형별 점수·사례별 실패·누락·측정값·실행 조건 |
| `<case-id>.review-template.json` | 답을 채우지 않은 사람 검토 양식 |

자동 통과와 최종 승인을 구분합니다. 검토가 없으면 `pending-review`이며 기본 종료 코드는 0입니다. `--strict`를 추가하면 18개 모두 자동 검사와 사람 검토를 통과해야 0입니다. 일부 사례 실행은 전체 승인으로 처리하지 않습니다.

## 변경된 분석 결과 비교

새 후보는 [사례 목록](../eval/cases.md)의 질문·대상·포함/제외 범위·언어·프로파일·고정 커밋을 유지한 내부 IR로 준비합니다. 사례별 `<case-id>.json`을 한 디렉터리에 넣습니다. 표시 제목·라벨·노드 ID는 바꿀 수 있으며, 역할의 허용 코드 이름과 소스 위치는 [정답 후보](../eval/m15/expectations/)에 있습니다. 질문이나 범위를 바꾸면 같은 사례 비교로 인정하지 않습니다.

~~~sh
npm run eval:run -- --candidates build/my-candidates --output build/eval/changed
npm run eval:compare -- build/eval/m15/results.json build/eval/changed/results.json
~~~

저장된 기준 기록과 비교하려면 첫 경로에 `eval/runs/2026-09-06-baseline.json`을 사용합니다. 이는 사람 승인 전 임시 기준입니다. 정답 또는 소스 구성이 달라지면 비교 불가로 표시하며, `no-regression`도 사람 승인을 의미하지 않습니다. 필수 요소 누락, 새로운 오류, 치명적 오류, 기존 승인 상실은 개별 사례로 보고합니다.

`--case utility-strip --case plugin-hooks`처럼 반복 지정해 일부만 실행할 수도 있습니다. 공통 지침 변경은 유형별 최소 1개와 과거 실패 사례, 특정 프로파일 변경은 해당 3개와 다른 유형 최소 3개, 공통 렌더러·스키마·검증기 변경은 전체 18개를 선택합니다. 도구가 변경 파일로 이 집합을 자동 선택하지는 않습니다.

## 사람 검토 반영

[루브릭](../eval/rubric.md)에 따라 정답 후보와 실제 HTML을 소스와 대조합니다. 생성된 양식을 `build/reviews/<case-id>.json` 같은 별도 경로에 복사해 검토자·ISO 시각·각 판정을 채웁니다. `facts`와 `forbidden`의 번호는 정답 파일의 배열 순서이며, 금지 주장은 **없어야** pass입니다. 추가 노드·관계와 모든 본문·캡션도 검토합니다. 양식의 해시는 수정하지 않습니다.

~~~sh
npm run eval:run -- --reviews build/reviews --output build/eval/reviewed --strict
~~~

후보·정답·지침/렌더러/평가 코드/루브릭이 바뀌면 기존 답변은 오래된 검토로 판정합니다. 외부 후보를 검토했다면 재실행에도 같은 `--candidates`를 지정합니다. 소스 위치가 맞다는 것만으로 문장·수치가 정확하다고 승인하지 않습니다.

## 사례 유지보수

`eval/m15/author_cases.py`는 기록된 12개 추가 분석을 재현하고 기존 M1 6개 분석을 복사하는 개발용 원장입니다. 새 저장소를 자동 탐색하지 않습니다. 원장이나 정답을 변경하기 전에 고정 소스를 다시 읽습니다. 원장을 재실행하면 후보의 생성 시각·해시가 바뀌며 재검토가 필요합니다. 기존 정답 파일은 자동 덮어쓰기하지 않으므로 정답 변경은 `expectations/`와 원장을 명시적으로 함께 편집합니다.

평가 입력·출처·선택한 기준 기록은 `eval/`에서 관리하고, 매 실행의 HTML·전체 출력·임시 답변은 Git에서 제외되는 `build/`에 보관합니다. 생성 모델·토큰·비용·탐색 시간은 측정한 값이 없으면 null로 남습니다. 평가 실행 시간과 근거 줄 수를 생성 비용 또는 전체 소스 탐색량으로 해석하지 않습니다.
