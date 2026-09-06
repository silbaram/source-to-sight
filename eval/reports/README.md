# 검증 및 리뷰 기록

개발 단계별 검증 결과, 코드리뷰, 사람 검토 자료와 해당 기록의 스크린샷을 보존합니다. 각 문서의 날짜와 대상 버전을 기준으로 읽으며, 과거 검사 결과를 현재 전체 제품의 완료 판정으로 해석하지 않습니다.

| 기록 | 내용 |
| --- | --- |
| [M0 검증](m0-verification.md) | 공통 IR·렌더러의 초기 구현과 검증 |
| [M0 코드리뷰](m0-review.md) | 최초 발견 사항, 수정 결과와 당시 재현 절차 |
| [M1 검증](m1-verification.md) | 범용 스킬·작성 도구·실제 사례와 최신 자동 검사 |
| [M1 사람 검토 자료](m1-human-review.md) | 근거 사실 확인·이해도 검토용 답변지. 검토 대기 |
| [M1.5 검증](m15-verification.md) | 18개 후보·비교 도구·검토 게이트와 자동 검사 |
| [M1.5 임시 기준](../runs/2026-09-06-baseline.md) | 저장된 후보 18개 재실행. 사람 승인 대기 |
| [M2 검증](m2-verification.md) | 복합 동작 지침·분기/실행 방식·24개 평가. 사람 승인 대기 |
| [M2 자동재생 표시 수정](m2-playback-verification.md) | 모든 단계의 진행 표시·병렬 노드 강조·가시 영역·정지 후 이어 재생 |
| [M2 병렬 진입 연결 수정](m2-parallel-handoffs-verification.md) | 3→4단계 진입과 확인된 호출·결과 기록의 이동 복원 |
| [부드러운 화면 이동](smooth-camera-verification.md) | 노드·연결을 따라 이동, 도착 후 재생, 직접 조작·모션 설정·창 크기 변경 |
| [공통 캔버스 검증](canvas-viewer-verification.md) | 실제 생성 템플릿의 UI 적용·회귀 검사 |
| [상세 패널 영역 수정](panel-bounds-verification.md) | 긴 설명·낮은 창에서 패널 이탈과 조작 버튼 가림 수정 |
| [연결 이동 애니메이션](flow-animation-verification.md) | 자동재생의 이동 표시·도착 강조·방향 이름·모션 설정 검사 |
| [디자인 시안 검증](design/atlas-prototype-verification.md) | 합성 데이터로 만든 UI 시안의 브라우저 검사 |

`qa/`와 `design/qa/`는 위 기록에서 참조하는 화면 자료입니다. 매번 생성되는 전체 HTML·스크린샷·실행 보고서는 Git에서 제외되는 `build/`, `test-results/`, `playwright-report/`에 둡니다. 선택해 보존하는 기준 기록은 `eval/runs/`에 둡니다. 평가 입력과 소스 출처는 [평가 사례 목록](../cases.md)과 [M1 사례](../m1/README.md)에 있습니다.

프로젝트 설명과 사용·개발 안내는 [docs](../../docs/README.md), 개발계획과 UI 설계 제안·시안은 [plans](../../plans/)에서 관리합니다.
