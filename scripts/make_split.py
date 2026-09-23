#!/usr/bin/env python3
"""검진 기록 원본(43,400명)을 캐글 방식으로 나눈다.

  data/train.csv              30,380명 · 정답(stroke) 있음 · 참가자에게 준다
  data/test.csv               13,020명 · 정답 없음 · 참가자는 이 사람들 중 전화를 걸 id를 제출한다
  data/sample_submission.csv  제출 양식(id, call)
  _private/labels.sql         test의 정답과 공개/최종 구분 · 수파베이스에만 넣는다 · 저장소에 올리지 않는다
  _private/test_labels.csv    같은 내용 csv(진행자 확인용)

나누는 규칙은 실습실이 전부터 쓰던 것과 같다: 원본을 id 순으로 정렬해 index % 10 < 3 이면 test.
id는 새로 매긴다(원본 id로 정답을 찾아보지 못하게). 공개/최종은 test 안에서 환자 여부로 층화한 무작위 절반.
실행: python3 scripts/make_split.py <원본 csv>
"""
import sys, pathlib
import numpy as np, pandas as pd

여기 = pathlib.Path(__file__).resolve().parent.parent
원본 = pd.read_csv(sys.argv[1]).sort_values("id").reset_index(drop=True)
test마스크 = np.asarray(원본.index % 10) < 3
rng = np.random.default_rng(20260923)

train = 원본[~test마스크].sample(frac=1, random_state=1).reset_index(drop=True)
test = 원본[test마스크].sample(frac=1, random_state=2).reset_index(drop=True)
train["id"] = np.arange(1, len(train) + 1)
test["id"] = np.arange(100001, 100001 + len(test))
# 공개/최종은 환자 여부로 층화해 절반씩 나눈다(환자도 절반, 환자 아닌 사람도 절반)
part = np.empty(len(test), dtype=object)
for 값 in (0, 1):
    자리 = np.flatnonzero(test["stroke"].to_numpy() == 값)
    섞은자리 = rng.permutation(자리)
    절반 = len(섞은자리) // 2
    part[섞은자리[:절반]] = "public"
    part[섞은자리[절반:]] = "private"

정답 = pd.DataFrame({"id": test["id"], "stroke": test["stroke"].astype(int), "part": part})
test = test.drop(columns=["stroke"])

(여기 / "data").mkdir(exist_ok=True); (여기 / "_private").mkdir(exist_ok=True)
train.to_csv(여기 / "data/train.csv", index=False)
test.to_csv(여기 / "data/test.csv", index=False)
pd.DataFrame({"id": test["id"], "call": 0}).to_csv(여기 / "data/sample_submission.csv", index=False)
정답.to_csv(여기 / "_private/test_labels.csv", index=False)

줄 = ",\n".join(f"({r.id},{r.stroke},'{r.part}')" for r in 정답.itertuples())
(여기 / "_private/labels.sql").write_text(
    "-- test 13,020명의 정답. 수파베이스 SQL Editor에서 schema.sql 다음에 실행한다. 저장소에 올리지 않는다.\n"
    "delete from public.stroke_challenge_labels;\n"
    "insert into public.stroke_challenge_labels (id, stroke, part) values\n" + 줄 + ";\n", encoding="utf-8")

print(f"train {len(train):,}명 · 환자 {int(train.stroke.sum())}명")
print(f"test  {len(test):,}명 · 환자 {int(정답.stroke.sum())}명 · 공개 {int((정답.part=='public').sum()):,}명(환자 {int(정답[정답.part=='public'].stroke.sum())}) · 최종 {int((정답.part=='private').sum()):,}명(환자 {int(정답[정답.part=='private'].stroke.sum())})")
