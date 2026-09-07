# 배포 파일 기준

이 저장소는 실행 가능한 스킬과 개발·검증 기록을 함께 관리합니다. 정식 제품으로 배포할 때는 스킬 패키지와 사용자 안내만 배포 범위로 취급하고, 평가 입력·실행 결과·시안은 검증 보관물로 취급합니다.

## 제품 배포 범위

다음 경로가 실제 사용자에게 제공되는 제품입니다.

- `skills/code-flow/`: 소스 기반 동작 설명 스킬, 렌더러, 스키마, 참고자료와 라이선스
- `skills/visual-primer/`: 개념·규칙 설명 스킬과 화면 템플릿
- `skills/codebase-atlas/`: 프로젝트 지도 생성 스킬
- `README.md`, `README.ko.md`, `docs/README.md`: 설치·사용·지원 범위 안내
- `assets/`: 저장소에서 바로 열어 볼 수 있는 대표 예시

스킬을 설치할 때는 각 `skills/<name>/` 디렉터리를 통째로 포함해야 합니다. `templates/vendor/`의 폰트·Dagre 파일과 라이선스도 런타임 렌더링에 필요하므로 제외하지 않습니다.

## 개발·검증 보관 범위

다음 경로는 제품 런타임에 필요하지 않으며 자동·사람 검토를 재현하기 위한 자료입니다.

- `eval/`: 사례 manifest, 그래프·정답·원장, 검증 보고서, QA 스크린샷, 보존한 M5 HTML/JSON
- `fixtures/`: 계약·렌더러 테스트 입력과 고정 소스 출처
- `tests/`: Python·Playwright 회귀 검사
- `scripts/`: 사례 생성, 평가 실행, 소스 수집과 벤더 갱신용 유지보수 도구
- `plans/`: 개발 계획과 UI 시안·프로토타입
- `package.json`, `package-lock.json`, `playwright.config.cjs`: 개발 환경과 검사 실행 설정

`eval/m5/html/`의 HTML은 GitHub에서 결과를 확인하기 위한 보존본입니다. 생성기의 기본 템플릿은 `skills/code-flow/templates/flow-viewer-template.html`과 `skills/visual-primer/templates/`에 있으며, 보존 HTML을 새 결과 생성에 사용하지 않습니다.

## 생성 결과와 배포 결과 구분

매번 생성되는 HTML·render JSON·스크린샷·실행 보고서는 `build/`에 두며 Git에서 추적하지 않습니다. 검토자가 다시 확인해야 하는 선별 결과만 `eval/`에 보존합니다. 따라서 `build/`는 배포 디렉터리가 아니고, `eval/`의 파일도 설치 패키지에 포함할 런타임 자원이 아닙니다.

GitHub 저장소에는 검증 기록이 남아 있어 릴리스 품질과 재현성을 확인할 수 있습니다. `git archive`로 제품 소스 묶음을 만들 때는 `.gitattributes`의 `export-ignore` 규칙이 검증·개발 전용 경로를 자동으로 제외합니다. GitHub 웹에서 해당 기록을 읽거나 평가를 재실행하는 데는 영향을 주지 않습니다.

