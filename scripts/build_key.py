#!/usr/bin/env python3
"""뇌졸중 예측 챌린지 정답표를 만든다 — key.js

앱이 열어 둔 설정을 모두 돌려 (안내 인원, 찾아낸 환자)를 적어 둔다.
순위판은 이 표로 올라온 기록이 실제로 나올 수 있는 값인지 대조한다.
설정과 결과는 일대일로 정해지므로, 표와 다르면 손으로 고친 기록이다.

열쇠 형식: 빈값처리(0·1) + 가중치(0·1) + 속성번호 + 모델(L, 또는 T와 질문 횟수)
값 형식: 기준값 0.05~0.95(0.05 간격) 차례대로 [안내 인원, 찾아낸 환자] 19쌍
2026-09-23부터 기준값을 두 모델 모두에 적용한다. 그 전의 트리 기록은 기준값과 상관없이
predict로 채점됐다. 확률이 정확히 0.5인 잎에서 predict는 0으로, 기준 0.50은 1로 답하므로
둘이 다를 수 있다. 그래서 옛 결과를 P+질문 횟수 칸에 [안내 인원, 찾아낸 환자]로 따로 둔다.
이 설명은 key.js에 적지 않는다. 적어 두면 학생이 파일을 열어 최댓값을 바로 찾아낸다.

실행: 실습실과 같은 Pyodide에서 돌려야 한다 — scripts/build_key_pyodide.mjs
      (python3로 직접 돌리면 컴퓨터의 scikit-learn 판에 따라 깊은 트리 몇 칸이 달라진다)
"""
import itertools, json, os, sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

데이터주소 = "https://raw.githubusercontent.com/greatsong/modudata/main/data/stroke.csv"
결과파일 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "key.js")
고를수있는열 = ["age", "avg_glucose_level", "bmi", "hypertension", "heart_disease"]
기준값들 = [round(0.05 * i, 2) for i in range(1, 20)]
깊이들 = list(range(1, 11))

def 채점(확률, 실제):
    """기준값마다 [안내 인원, 찾아낸 환자]를 차례로 적는다."""
    return [[int((확률 >= 기준).sum()), int(((확률 >= 기준) & (실제 == 1)).sum())] for 기준 in 기준값들]


원본 = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else 데이터주소, encoding="utf-8")
표, 머리 = {}, {}

for 결측번호, 결측 in enumerate(("그대로 둔다", "지운다")):
    df = 원본 if 결측 == "그대로 둔다" else 원본.dropna(subset=["bmi"])
    df = df.sort_values("id").reset_index(drop=True)
    테스트용 = pd.Series(df.index % 10 < 3, index=df.index)
    y = df["stroke"]
    머리[결측번호] = {"n": int(테스트용.sum()), "pos": int(y[테스트용].sum())}

    for 개수 in range(2, 6):
        for 뽑기 in itertools.combinations(range(5), 개수):
            열들 = [고를수있는열[i] for i in 뽑기]
            X = df[열들].copy()
            if "bmi" in 열들 and X["bmi"].isna().any():
                X["bmi"] = X["bmi"].fillna(float(X.loc[~테스트용, "bmi"].median()))
            Xtr, ytr, Xte = X[~테스트용], y[~테스트용], X[테스트용]
            실제 = y[테스트용].to_numpy()
            속성키 = "".join(str(i) for i in 뽑기)

            for 무게번호, 무게 in enumerate((None, "balanced")):
                맞추기 = StandardScaler().fit(Xtr)
                로지 = LogisticRegression(max_iter=2000, class_weight=무게).fit(맞추기.transform(Xtr), ytr)
                확률 = 로지.predict_proba(맞추기.transform(Xte))[:, 1]
                표[f"{결측번호}{무게번호}{속성키}L"] = 채점(확률, 실제)
                for 깊이 in 깊이들:
                    트리 = DecisionTreeClassifier(max_depth=깊이, min_samples_leaf=5,
                                                  random_state=0, class_weight=무게).fit(Xtr, ytr)
                    트리확률 = 트리.predict_proba(Xte)[:, 1]
                    표[f"{결측번호}{무게번호}{속성키}T{깊이}"] = 채점(트리확률, 실제)
                    옛예측 = 트리.predict(Xte)              # 기준값을 쓰지 않던 때의 트리 기록과 대조할 값
                    표[f"{결측번호}{무게번호}{속성키}P{깊이}"] = [
                        int(옛예측.sum()), int(((실제 == 1) & (옛예측 == 1)).sum())]

본문 = json.dumps({"head": 머리, "key": 표}, separators=(",", ":"))
with open(결과파일, "w", encoding="utf-8") as f:
    f.write("// scripts/build_key.py가 다시 쓴다. 손으로 고치지 않는다.\n")
    f.write("window.CHALLENGE_KEY = " + 본문 + ";\n")
print(f"key.js {os.path.getsize(결과파일)/1024:.1f}KB · 칸 {len(표):,}개")
print("테스트 데이터:", 머리)
