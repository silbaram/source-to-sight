"""Create a human-review worksheet without replacing existing reviewer answers."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/code-flow/scripts"))
import s2s


def worksheet():
    lines = ["# M1 사람 검토용 자료", "", "상태: **검토 대기**. 코딩 에이전트의 소스 재독해·자동 검사는 사람의 사실 확인이나 이해도 검토를 대신하지 않습니다.",
             "", "각 사례의 페이지를 먼저 읽고 목적·입력/결과·주요 동작·중요한 제한을 자신의 말로 설명해 주세요. 그 뒤 아래 근거의 위치와 주장 내용이 모두 맞는지 확인합니다.",
             "유형별 근거 위치를 최대 다섯 개 선정했습니다. 위치가 다섯 개보다 적으면 전부 확인합니다. 하나의 위치가 여러 주장을 지원할 수 있으므로 연결된 주장도 함께 검토합니다.", ""]
    for case in json.loads((ROOT / "eval/m1/cases.json").read_text()):
        graph = json.loads((ROOT / "eval/m1" / case["graph"]).read_text())
        snapshot = graph["snapshot"]
        lines += [f"## {case['id']}", "", f"질문: {case['question']}", "",
                  f"프로파일: {', '.join(case['profiles'])} · 소스 언어: {case['language']}", "",
                  f"로컬 결과: `build/m1/{case['output']}` · 커밋: `{snapshot['commit']}`", "",
                  "검토자: 미지정 · 검토일: 미지정 · 결과: 대기", "",
                  "| 근거 | 연결된 주장과 검토 포인트 | 위치 확인 | 내용 확인 |", "| --- | --- | --- | --- |"]
        for evidence in graph["evidence"][:5]:
            supported = [item for item in s2s.claims(graph) if evidence["id"] in item.get("evidenceIds", [])]
            labels = list(dict.fromkeys(item.get("label", item.get("plainText", item.get("caption", item["id"]))) for item in supported))
            text = " / ".join(labels).replace("|", "\\|").replace("\n", " ")
            path, start, end = evidence["file"], evidence["startLine"], evidence["endLine"]
            url = f"https://github.com/{snapshot['repository']}/blob/{snapshot['commit']}/{path}#L{start}-L{end}"
            lines.append(f"| [{path}:{start}–{end}]({url}) | {text} | 대기 | 대기 |")
        lines += ["", "이해 확인 답변:", "", "- 이 기능의 목적:", "- 입력과 결과:", "- 주요 동작 또는 관계:", "- 중요한 제한과 아직 모르는 부분:", "", "수정이 필요한 주장 또는 이해하기 어려운 부분:", ""]
    lines += ["## 판정", "", "여섯 유형의 위치·내용 확인과 이해 확인이 끝나기 전에는 M1 최종 게이트를 통과 처리하지 않습니다. 독립적인 모델 평가와 사람 검토를 혼동하지 않습니다.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/m1/human-review.md")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(worksheet())
    print(args.output)
