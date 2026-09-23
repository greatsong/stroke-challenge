# pages/4_성능_높이기.py — 전후를 나란히 놓고 채점한 뒤, 설정을 바꿔 가며 최고 점수에 도전한다
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

st.set_page_config(page_title="성능 높이기", page_icon="🏆", layout="wide")
st.title("🏆 성능 높이기")
st.write("데이터를 손보고 다시 학습해 전후를 나란히 놓고 본 뒤, 설정을 바꿔 가며 더 좋은 점수에 도전합니다.")

고를수있는열 = ["age", "avg_glucose_level", "bmi", "hypertension", "heart_disease",
              "married", "smokes", "self_employed", "male"]
기본열 = ["age", "avg_glucose_level", "hypertension", "heart_disease"]
입력이름 = {"age": "나이", "avg_glucose_level": "평균 혈당", "bmi": "체질량지수",
            "hypertension": "고혈압", "heart_disease": "심장병", "married": "결혼 여부",
            "smokes": "현재 흡연", "self_employed": "자영업", "male": "남성"}

from 공용 import 설정_읽기, 속성_더하기, 데이터_읽기 as 공용_데이터_읽기, 테스트_읽기, 호출, 행사_정보
챌린지설정 = 설정_읽기()
전이름, 후이름 = "고치기 전 (가중치 그대로)", "고친 뒤 (가중치를 같게)"
칸수, 칸수3D = 60, 26


@st.cache_data
def 데이터_읽기():
    return 속성_더하기(공용_데이터_읽기())

def 우리말(열):
    return 입력이름[열]

원본 = 데이터_읽기()

고른열 = st.multiselect("입력으로 사용할 속성", 고를수있는열, default=기본열, format_func=우리말,
                        help="처음에는 나이·평균 혈당·고혈압·심장병 네 가지가 골라져 있습니다. "
                             "결혼 여부·현재 흡연·자영업·남성은 예(1)·아니요(0)로 바꾼 속성입니다.")
입력열 = [열 for 열 in 고를수있는열 if 열 in 고른열]   # 고른 차례와 상관없이 늘 같은 순서로 둔다
if len(입력열) < 2:
    st.warning("속성을 두 개 이상 골라 주세요. 하나만으로는 그림의 두 축을 만들 수 없습니다.")
    st.stop()

빈값이름 = {"지운다": "지운다", "그대로 둔다": "중앙값으로 채운다"}   # 기록에는 왼쪽 이름으로 저장한다


def 나누기(결측처리, 열=None):
    """'채점표' 페이지와 같은 방법으로 훈련용과 검증용을 먼저 나눈 뒤 빈 값을 처리한다.
    원본을 id 순으로 정렬해 index % 10 < 3 이면 검증용이다. 검증 여부를 지우기 전에 정하므로
    「지운다」의 검증용은 「중앙값으로 채운다」의 검증용에서 체질량지수가 빈 사람만 빠진 같은 사람들이다."""
    열 = 입력열 if 열 is None else list(열)
    df = 원본.sort_values("id").reset_index(drop=True)
    검증표시 = np.asarray(df.index % 10 < 3)
    if 결측처리 == "지운다":
        남김 = df["bmi"].notna().to_numpy()
        df, 검증표시 = df[남김].reset_index(drop=True), 검증표시[남김]
    검증용 = pd.Series(검증표시, index=df.index)
    X = df[열].copy()
    if "bmi" in 열 and X["bmi"].isna().any():
        X["bmi"] = X["bmi"].fillna(float(X.loc[~검증용, "bmi"].median()))   # 훈련용의 중앙값으로 채운다
    return df, 검증용, X, df["stroke"]


# 위쪽 비교는 전체 데이터로 한다. 빈 값 처리는 아래 챌린지에서 고른다
df, 검증용, X, y = 나누기("그대로 둔다")
실제 = y[검증용].to_numpy()
if "bmi" in 입력열:
    st.warning(f"체질량지수가 비어 있는 {int(원본['bmi'].isna().sum()):,}명은 훈련용의 중앙값으로 채웠습니다.")
st.info(f"사용하는 사람은 {len(df):,}명이고 그중 뇌졸중은 {int(y.sum()):,}명입니다 · "
        f"검증용 {len(실제):,}명 가운데 실제 뇌졸중은 {int(실제.sum()):,}명입니다.")

def 학습(가중치):
    """가중치를 맞출지 정해 두 모델을 학습해 돌려준다."""
    맞춤 = "balanced" if 가중치 else None
    크기맞추기 = StandardScaler().fit(X[~검증용])
    확률모델 = LogisticRegression(max_iter=2000, class_weight=맞춤).fit(
        크기맞추기.transform(X[~검증용]), y[~검증용])
    질문모델 = DecisionTreeClassifier(max_depth=3, min_samples_leaf=5, random_state=0,
                                      class_weight=맞춤).fit(X[~검증용], y[~검증용])
    return 크기맞추기, 확률모델, 질문모델

모델 = {전이름: 학습(False), 후이름: 학습(True)}
예측 = {}
for 상태, (크기맞추기, 확률모델, 질문모델) in 모델.items():
    예측[상태] = {"확률로 답하는 모델": 확률모델.predict(크기맞추기.transform(X[검증용])),
                  "질문으로 답하는 모델": 질문모델.predict(X[검증용])}

def 네칸(실제값, 예측값):
    """검증용뿐 아니라 훈련용도 셀 수 있도록 실제값을 함께 받는다."""
    TP = int(((실제값 == 1) & (예측값 == 1)).sum())
    FN = int(((실제값 == 1) & (예측값 == 0)).sum())
    FP = int(((실제값 == 0) & (예측값 == 1)).sum())
    TN = int(((실제값 == 0) & (예측값 == 0)).sum())
    return TP, FN, FP, TN

def 지표(TP, FN, FP, TN):
    정확도 = (TP + TN) / (TP + FN + FP + TN)
    정밀도 = TP / (TP + FP) if (TP + FP) > 0 else None
    재현율 = TP / (TP + FN) if (TP + FN) > 0 else None
    # F1은 정밀도와 재현율로만 구한다. 둘 중 하나라도 없거나 합이 0이면 구할 수 없다
    F1 = (2 * 정밀도 * 재현율 / (정밀도 + 재현율)
          if 정밀도 is not None and 재현율 is not None and (정밀도 + 재현율) > 0 else None)
    return 정확도, 정밀도, 재현율, F1

정식이름 = {"확률로 답하는 모델": "로지스틱 회귀", "질문으로 답하는 모델": "의사결정트리",
            "랜덤 포레스트": "랜덤 포레스트", "그레이디언트 부스팅": "그레이디언트 부스팅",
            "k-최근접 이웃": "k-최근접 이웃"}

def 병기(이름):
    """교과서의 정식 이름을 앞에 두고 교재에서 쓰는 이름을 괄호로 붙인다. 교재 이름이 따로 없으면 정식 이름만 쓴다."""
    if 이름 not in 정식이름 or 정식이름[이름] == 이름:
        return 이름
    return f"{정식이름[이름]}({이름})"

def 소수(값):
    return "계산할 수 없음" if 값 is None else f"{값:.4f}"

st.subheader("고치기 전과 고친 뒤")
for 모델이름 in ("확률로 답하는 모델", "질문으로 답하는 모델"):
    st.markdown(f"**{병기(모델이름)}**")
    칸 = {}
    for 상태 in 예측:
        TP, FN, FP, TN = 네칸(실제, 예측[상태][모델이름])
        정확도, 정밀도, 재현율, F1 = 지표(TP, FN, FP, TN)
        칸[상태] = [f"{TP}명", f"{FP}명", f"{FN}명", f"{TN:,}명",
                    소수(정확도), 소수(재현율), 소수(정밀도), 소수(F1)]
    비교표 = pd.DataFrame(칸, index=["TP (찾아낸 환자)", "FP (헛짚은 사람)", "FN (놓친 환자)", "TN",
                                     "정확도", "재현율", "정밀도", "F1"])
    비교표.index.name = ""
    st.table(비교표)
    전 = 네칸(실제, 예측[전이름][모델이름])
    후 = 네칸(실제, 예측[후이름][모델이름])
    st.caption(f"찾아낸 환자 {전[0]}명 → {후[0]}명 · 놓친 환자 {전[1]}명 → {후[1]}명 · "
               f"헛짚은 사람 {전[2]}명 → {후[2]}명")

st.subheader("가중치를 맞추자 경계선이 어디로 움직였는가")
축칸 = st.columns(2)
가로 = 축칸[0].selectbox("가로축", 입력열, index=0, format_func=우리말)
세로후보 = [열 for 열 in 입력열 if 열 != 가로]
세로 = 축칸[1].selectbox("세로축", 세로후보, index=0, format_func=우리말)

채점입력 = X[검증용]
고정값 = {열: float(채점입력[열].median()) for 열 in 입력열 if 열 not in (가로, 세로)}
색깔 = {전이름: "#2563eb", 후이름: "#dc2626"}

def 눈금(열, 개수):
    """검증용에서의 가장 작은 값부터 가장 큰 값까지 고르게 나눈 값들을 돌려준다."""
    작은값, 큰값 = float(채점입력[열].min()), float(채점입력[열].max())
    if 큰값 <= 작은값:
        큰값 = 작은값 + 1.0
    폭 = (큰값 - 작은값) / (개수 - 1)
    return [작은값 + 폭 * i for i in range(개수)]

def 두줄로(값들, 개수):
    """한 줄로 늘어선 값을 세로줄마다 잘라 표 모양으로 만든다."""
    return [값들[i * 개수:(i + 1) * 개수] for i in range(개수)]

가로눈금, 세로눈금 = 눈금(가로, 칸수), 눈금(세로, 칸수)
격자 = pd.DataFrame([dict(고정값, **{가로: 가, 세로: 세}) for 세 in 세로눈금 for 가 in 가로눈금])[입력열]

그림2D = go.Figure()
밖으로나간것 = []
for 상태 in (전이름, 후이름):
    크기맞추기, 확률모델, _ = 모델[상태]
    확률격자 = 확률모델.predict_proba(크기맞추기.transform(격자))[:, 1].tolist()
    그림2D.add_trace(go.Contour(x=가로눈금, y=세로눈금, z=두줄로(확률격자, 칸수),
                                contours=dict(coloring="lines", start=0.5, end=0.5, size=1),
                                line=dict(width=3, color=색깔[상태]), showscale=False,
                                hoverinfo="skip", name=f"{상태}의 0.5 경계선"))
    if not (min(확률격자) <= 0.5 <= max(확률격자)):
        밖으로나간것.append((상태, max(확률격자)))

점표 = pd.DataFrame({
    "가로": 채점입력[가로].to_numpy(), "세로": 채점입력[세로].to_numpy(),
    "실제": pd.Series(실제).map({1: "뇌졸중 있음", 0: "뇌졸중 없음"}).to_numpy(),
})
for 이름, 색 in (("뇌졸중 없음", "#94a3b8"), ("뇌졸중 있음", "#7f1d1d")):
    한그룹 = 점표[점표["실제"] == 이름]
    그림2D.add_trace(go.Scatter(x=한그룹["가로"], y=한그룹["세로"], mode="markers", name=이름,
                                marker=dict(size=6, color=색, opacity=0.5,
                                            line=dict(width=0.5, color="white"))))
그림2D.update_layout(title=f"가로축 {우리말(가로)} · 세로축 {우리말(세로)} · 전후 경계선",
                     xaxis_title=우리말(가로), yaxis_title=우리말(세로), height=560)
st.plotly_chart(그림2D, width="stretch")
for 상태, 가장높은확률 in 밖으로나간것:
    st.info(f"{상태}: 이 그림 안에서 확률이 가장 높은 자리도 {가장높은확률:.2f}입니다. "
            f"확률이 0.5를 넘는 자리가 없어 0.5 경계선이 그림 안에 없습니다.")
고정설명 = " · ".join(f"{우리말(열)} {값:g}" for 열, 값 in 고정값.items())
st.caption(f"파란 선은 고치기 전, 붉은 선은 고친 뒤의 0.5 경계선입니다. 점은 검증 데이터이고 색은 실제 "
           f"뇌졸중 여부입니다."
           + (f" 두 축이 아닌 속성은 검증 데이터의 중앙값({고정설명})으로 고정해 계산했습니다." if 고정값 else ""))

if len(입력열) >= 3:
    st.subheader("축 셋으로 돌려 보기")
    세축 = st.multiselect("3차원 산점도의 축 셋", 입력열, default=입력열[:3], max_selections=3,
                          format_func=우리말)
    if len(세축) != 3:
        st.info("축을 정확히 세 개 골라 주세요.")
    else:
        가1, 가2, 가3 = 세축
        자리 = {열: 번호 for 번호, 열 in enumerate(입력열)}
        눈금1, 눈금2 = 눈금(가1, 칸수3D), 눈금(가2, 칸수3D)
        낮은끝, 높은끝 = float(채점입력[가3].min()), float(채점입력[가3].max())
        그림3D = go.Figure()
        없는평면 = []
        for 상태 in (전이름, 후이름):
            크기맞추기, 확률모델, _ = 모델[상태]
            계수 = 확률모델.coef_[0].tolist()
            절편 = float(확률모델.intercept_[0])
            평균, 폭 = 크기맞추기.mean_.tolist(), 크기맞추기.scale_.tolist()

            def 크기맞춘값(열, 값, 계수=계수, 평균=평균, 폭=폭):
                i = 자리[열]
                return 계수[i] * (값 - 평균[i]) / 폭[i]

            세로3 = 자리[가3]
            평면 = None
            if 계수[세로3] != 0:
                남은값 = sum(크기맞춘값(열, float(채점입력[열].median()))
                             for 열 in 입력열 if 열 not in 세축)
                평면 = []
                for 값2 in 눈금2:
                    한줄 = []
                    for 값1 in 눈금1:
                        합 = 절편 + 남은값 + 크기맞춘값(가1, 값1) + 크기맞춘값(가2, 값2)
                        해 = 평균[세로3] - 폭[세로3] * 합 / 계수[세로3]
                        한줄.append(해 if 낮은끝 <= 해 <= 높은끝 else None)
                    평면.append(한줄)
                if all(값 is None for 한줄 in 평면 for 값 in 한줄):
                    평면 = None
            if 평면 is None:
                없는평면.append(상태)
            else:
                그림3D.add_trace(go.Surface(x=눈금1, y=눈금2, z=평면, showscale=False, opacity=0.45,
                                            colorscale=[[0, 색깔[상태]], [1, 색깔[상태]]],
                                            hoverinfo="skip", name=f"{상태}의 0.5 평면"))
        점표3 = pd.DataFrame({
            "축1": 채점입력[가1].to_numpy(), "축2": 채점입력[가2].to_numpy(),
            "축3": 채점입력[가3].to_numpy(),
            "실제": pd.Series(실제).map({1: "뇌졸중 있음", 0: "뇌졸중 없음"}).to_numpy(),
        })
        for 이름, 색 in (("뇌졸중 없음", "#94a3b8"), ("뇌졸중 있음", "#7f1d1d")):
            한그룹 = 점표3[점표3["실제"] == 이름]
            그림3D.add_trace(go.Scatter3d(x=한그룹["축1"], y=한그룹["축2"], z=한그룹["축3"],
                                          mode="markers", name=이름,
                                          marker=dict(size=3, color=색, opacity=0.6)))
        그림3D.update_layout(height=620, scene=dict(xaxis_title=우리말(가1), yaxis_title=우리말(가2),
                                                    zaxis_title=우리말(가3)))
        st.plotly_chart(그림3D, width="stretch")
        for 상태 in 없는평면:
            st.info(f"{상태}: 확률 0.5 평면이 이 그림 안에 없습니다. 그림 안의 어느 자리에서도 확률이 0.5에 "
                    f"닿지 않기 때문입니다.")
        st.caption("마우스로 끌면 돌려 볼 수 있습니다. 파란 면은 고치기 전, 붉은 면은 고친 뒤의 0.5 평면입니다."
                   + (" 축 셋이 아닌 속성은 검증 데이터의 중앙값으로 고정해 계산했습니다." if len(입력열) > 3 else ""))

상태이름 = 후이름
st.subheader(f"{상태이름} · {병기('확률로 답하는 모델')}이 놓친 환자")
예측값 = 예측[상태이름]["확률로 답하는 모델"]
채점명단 = df[검증용].copy()
채점명단["고혈압"] = 채점명단["hypertension"].map({1: "있음", 0: "없음"})
채점명단["심장병"] = 채점명단["heart_disease"].map({1: "있음", 0: "없음"})
놓친환자 = 채점명단[(실제 == 1) & (예측값 == 0)].sort_values("age")
놓친환자 = 놓친환자[["id", "age", "고혈압", "심장병"]].rename(columns={"id": "번호", "age": "나이"})
st.markdown(f"**모두 {len(놓친환자):,}명**")
st.dataframe(놓친환자.head(20), width="stretch", hide_index=True)
st.caption("나이가 적은 순서로 앞 스무 줄까지만 보여 줍니다. 고혈압 칸과 심장병 칸을 함께 읽습니다.")


st.divider()
st.subheader("🏆 미션 · 상담 전화 대상 고르기")
행사 = 행사_정보(챌린지설정)


def 서울시각(값):
    """PostgREST는 시각을 UTC로 준다. 서울 시각으로 바꿔 적는다."""
    시각 = pd.Timestamp(값)
    if 시각.tzinfo is None:
        시각 = 시각.tz_localize("UTC")
    try:
        시각 = 시각.tz_convert("Asia/Seoul")
    except Exception:                                   # 시간대 자료가 없는 환경이면 +9시간으로 계산한다
        from datetime import timedelta, timezone
        시각 = 시각.tz_convert(timezone(timedelta(hours=9)))
    return 시각.strftime("%Y-%m-%d %H:%M")


if 행사:
    마감글 = ("마감 " + 서울시각(행사["deadline"])) if 행사.get("deadline") else "마감 없음"
    st.caption(f"행사 「{행사['title']}」 · {마감글} · 팀당 제출 {행사['max_submissions']}회 · "
               f"채점 대상 test 13,020명 가운데 공개 {행사['n_public']:,}명(환자 {행사['pos_public']}명), 최종 {행사['n_private']:,}명")
st.info("센터장의 편지대로 평가는 F2(재현율을 정밀도의 두 배로 치는 점수)입니다. 아래 점수는 train 안에서 떼어 둔 검증 데이터(30%)로 계산한 것입니다. "
        "제출하면 test의 공개 절반에 대한 점수가 순위판에 오르고, 최종 절반의 점수는 센터장이 공개할 때 열립니다.")
결측처리 = st.radio("체질량지수가 비어 있는 사람을 어떻게 할까요", list(빈값이름), horizontal=True,
                    format_func=빈값이름.get,
                    help="중앙값으로 채우면 비어 있는 칸을 훈련용 체질량지수의 중앙값으로 채웁니다.")
df, 검증용, X, y = 나누기(결측처리)                  # 여기부터는 미션에서 고른 빈 값 처리로 채점한다
if 결측처리 == "지운다":
    st.caption(f"체질량지수가 비어 있던 {len(원본) - len(df):,}명을 지웠습니다. 그 안에 뇌졸중 환자가 "
               f"{int(원본['stroke'].sum() - df['stroke'].sum()):,}명 들어 있었습니다. "
               f"검증용에 남은 뇌졸중 환자는 {int(y[검증용].sum())}명입니다.")

미션모델 = ["확률로 답하는 모델", "질문으로 답하는 모델", "랜덤 포레스트", "그레이디언트 부스팅", "k-최근접 이웃"]
고른모델 = st.multiselect("어떤 모델을 돌릴까요", 미션모델, default=미션모델[:2], format_func=병기,
                          help="고른 모델만 학습하고 채점합니다. 브라우저 안에서 계산하므로 모델을 늘리면 기다리는 시간이 길어집니다.")
if not 고른모델:
    st.warning("모델을 하나도 고르지 않아 로지스틱 회귀 하나로 계산합니다.")
    고른모델 = [미션모델[0]]
고른모델 = [이름 for 이름 in 미션모델 if 이름 in 고른모델]   # 고른 차례와 상관없이 늘 같은 순서로 둔다

st.caption("기본 설정은 가중치 그대로 · 질문 3번 · 기준값 0.50입니다. 미션에서는 모든 모델의 양쪽 가중치를 같게 맞춰 학습하고, "
           "빈 값을 지운 채 기준값 0.60에서 시작합니다. 기준값은 모든 모델에 적용됩니다. 확률이 기준값 이상이면 전화를 겁니다. "
           "k-최근접 이웃은 가중치를 맞추는 설정이 없어 그대로 학습합니다.")
조절2, 조절3 = st.columns(2)
내가중치 = True                                        # 미션에서는 늘 가중치를 같게 맞춘다
내깊이 = 조절2.slider("질문을 몇 번까지 던질까요", 1, 10, 3)
조절2.caption("질문 횟수는 의사결정트리에만 적용됩니다.")
내기준 = 조절3.slider("확률이 얼마 이상이면 전화를 걸까요", 0.05, 0.95, 0.60, 0.05)


def F2계산(정밀도, 재현율):
    """재현율을 정밀도의 두 배로 치는 점수. 둘 중 하나라도 없으면 계산할 수 없다."""
    if 정밀도 is None or 재현율 is None or 4 * 정밀도 + 재현율 == 0:
        return None
    return 5 * 정밀도 * 재현율 / (4 * 정밀도 + 재현율)


def 점수(값):
    return -1 if 값["F2"] is None else 값["F2"]


def 순서(값):
    """모델 가운데 앞선 쪽을 고르는 열쇠. 점수가 같으면 찾아낸 환자가 많은 쪽, 그다음 안내 인원이 적은 쪽."""
    return (점수(값), 값["찾아낸 환자"], -값["안내 인원"])


크기맞춤모델 = {"확률로 답하는 모델", "k-최근접 이웃"}   # 거리나 계수를 쓰는 모델은 속성의 크기를 맞춘다


def 깊이값(모델이름, 깊이):
    """질문 횟수는 의사결정트리에만 쓴다. 다른 모델은 0으로 두어 같은 학습을 다시 하지 않게 한다."""
    return 깊이 if 모델이름 == "질문으로 답하는 모델" else 0


def 모델만들기(모델이름, 가중치, 깊이):
    맞춤 = "balanced" if 가중치 else None
    if 모델이름 == "확률로 답하는 모델":
        return LogisticRegression(max_iter=2000, class_weight=맞춤)
    if 모델이름 == "질문으로 답하는 모델":
        return DecisionTreeClassifier(max_depth=깊이, min_samples_leaf=5, random_state=0, class_weight=맞춤)
    if 모델이름 == "랜덤 포레스트":
        return RandomForestClassifier(n_estimators=60, min_samples_leaf=5, class_weight=맞춤, random_state=0)
    if 모델이름 == "그레이디언트 부스팅":
        # early_stopping을 끈다. 켜 두면(표본 1만 명 이상일 때 기본값) 안에서 검증용을 떼는데,
        # 실습실(stlite)의 pyarrow 대역에 RecordBatch가 없어 오류가 난다. 150번을 모두 학습한다
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                              class_weight=맞춤, random_state=0, early_stopping=False)
    return KNeighborsClassifier(n_neighbors=50)


def 모델학습(모델이름, 가중치, 깊이, Xa, ya):
    """한 모델을 학습해 (크기 맞추기, 모델)을 돌려준다. 크기를 맞추지 않는 모델은 앞쪽이 None이다."""
    크기맞추기 = StandardScaler().fit(Xa) if 모델이름 in 크기맞춤모델 else None
    입력 = 크기맞추기.transform(Xa) if 크기맞추기 is not None else Xa
    return 크기맞추기, 모델만들기(모델이름, 가중치, 깊이).fit(입력, ya)


def 확률구하기(학습결과, Xb):
    """뇌졸중일 확률. 의사결정트리는 도착한 칸에서 뇌졸중이었던 사람의 비율이다."""
    크기맞추기, 모델 = 학습결과
    return 모델.predict_proba(크기맞추기.transform(Xb) if 크기맞추기 is not None else Xb)[:, 1]


def 전체데이터(결측처리, 열):
    """제출용: train 전체(빈 값 처리 반영)와 체질량지수를 채울 중앙값."""
    전체 = 원본 if 결측처리 == "그대로 둔다" else 원본.dropna(subset=["bmi"])
    Xa = 전체[list(열)].copy()
    중앙값 = float(Xa["bmi"].median()) if "bmi" in 열 else None
    if 중앙값 is not None:
        Xa["bmi"] = Xa["bmi"].fillna(중앙값)
    return Xa, 전체["stroke"], 중앙값


@st.cache_resource(show_spinner=False, max_entries=60)
def 실험학습(모델이름, 가중치, 깊이, 입력열튜플, 결측처리, 범위):
    """학습 결과를 설정마다 한 번만 만든다. 범위가 '훈련용'이면 검증용을 뺀 훈련용으로, '전체'면 train 전체로 학습한다."""
    if 범위 == "훈련용":
        _, 검, Xs, ys = 나누기(결측처리, 입력열튜플)
        return 모델학습(모델이름, 가중치, 깊이, Xs[~검], ys[~검])
    Xa, ya, _ = 전체데이터(결측처리, 입력열튜플)
    return 모델학습(모델이름, 가중치, 깊이, Xa, ya)


def 채점(모델이름, 설정, 자리):
    """한 설정으로 훈련용을 학습해 그 자리(훈련용 또는 검증용)의 네 칸과 다섯 지표를 돌려준다."""
    가중치, 깊이, 기준 = 설정
    학습결과 = 실험학습(모델이름, 가중치, 깊이값(모델이름, 깊이), tuple(입력열), 결측처리, "훈련용")
    예측값 = (확률구하기(학습결과, X[자리]) >= 기준).astype(int)
    TP, FN, FP, TN = 네칸(y[자리].to_numpy(), 예측값)
    정확도, 정밀도, 재현율, F1 = 지표(TP, FN, FP, TN)
    return TP, FN, FP, TN, 정확도, 정밀도, 재현율, F1, F2계산(정밀도, 재현율)


@st.cache_data(show_spinner=False, max_entries=60)
def 교차검증확률(모델이름, 깊이, 입력열튜플, 결측처리):
    """훈련용 안에서 5겹 교차검증으로 한 모델의 확률을 모은다. 검증 데이터를 보지 않고 설정을 고를 때의 기준이다."""
    from sklearn.model_selection import StratifiedKFold
    _, 검, Xs, ys = 나누기(결측처리, 입력열튜플)
    Xa, ya = Xs[~검].reset_index(drop=True), ys[~검].reset_index(drop=True)
    확률 = np.zeros(len(Xa))
    for 훈련, 평가 in StratifiedKFold(5, shuffle=True, random_state=0).split(Xa, ya):
        확률[평가] = 확률구하기(모델학습(모델이름, True, 깊이, Xa.iloc[훈련], ya.iloc[훈련]), Xa.iloc[평가])
    return 확률, ya.to_numpy()


def 교차키(모델이름):
    return (모델이름, 깊이값(모델이름, 내깊이), tuple(입력열), 결측처리)


기본설정 = (False, 3, 0.50)
내설정 = (내가중치, 내깊이, 내기준)

교차결과 = st.session_state.setdefault("교차검증결과", {})
if st.button("교차검증으로 확인하기"):
    시작 = time.time()
    with st.spinner("고른 모델마다 훈련용을 다섯 겹으로 나눠 학습하고 있습니다."):
        for 이름 in 고른모델:
            교차결과[교차키(이름)] = 교차검증확률(*교차키(이름))
    st.session_state["교차검증시간"] = time.time() - 시작

with st.spinner("고른 모델을 학습하고 채점하고 있습니다."):
    내기록 = {}
    for 모델이름 in 고른모델:
        TP, FN, FP, TN, 정확도, 정밀도, 재현율, F1, F2 = 채점(모델이름, 내설정, 검증용)
        내기록[모델이름] = {"찾아낸 환자": TP, "안내 인원": TP + FP, "정확도": 정확도,
                            "재현율": 재현율, "정밀도": 정밀도, "F1": F1, "F2": F2}
좋은모델, 값 = max(내기록.items(), key=lambda x: 순서(x[1]))


def 교차F2(모델이름):
    """교차검증 확률이 있으면 지금 기준값으로 F2를 계산한다. 버튼을 누르기 전이면 None."""
    결과 = 교차결과.get(교차키(모델이름))
    if 결과 is None:
        return None
    확률, 정답 = 결과
    TP, FN, FP, TN = 네칸(정답, (확률 >= 내기준).astype(int))
    _, 정밀도, 재현율, _ = 지표(TP, FN, FP, TN)
    return ("값", F2계산(정밀도, 재현율))


st.markdown("**지금 내 설정의 성적** · 검증 데이터 기준")
성적칸 = st.columns(4)
성적칸[0].metric("검증 F2", 소수(값["F2"]))
성적칸[1].metric("찾아낸 환자", f"{값['찾아낸 환자']}명", f"검증 환자 {int(y[검증용].sum())}명")
성적칸[2].metric("안내(전화) 인원", f"{값['안내 인원']:,}명")
성적칸[3].metric("정밀도 · 재현율", f"{소수(값['정밀도'])} · {소수(값['재현율'])}")
st.caption(f"위 네 칸은 고른 모델 가운데 검증 F2가 가장 높은 {병기(좋은모델)}의 성적입니다. 제출도 이 모델로 합니다.")

교차있음 = any(교차F2(이름) is not None for 이름 in 고른모델)
머리 = ["모델", "검증 F2", "찾아낸 환자", "안내 인원", "정밀도", "재현율", "F1"] + (["교차검증 F2"] if 교차있음 else [])
줄들 = ["| " + " | ".join(머리) + " |", "|" + "---|" * len(머리)]
for 이름 in 고른모델:
    기록 = 내기록[이름]
    칸 = [병기(이름), 소수(기록["F2"]), f"{기록['찾아낸 환자']}명", f"{기록['안내 인원']:,}명",
         소수(기록["정밀도"]), 소수(기록["재현율"]), 소수(기록["F1"])]
    if 교차있음:
        교차 = 교차F2(이름)
        칸.append("버튼을 누르면 계산" if 교차 is None else 소수(교차[1]))
    if 이름 == 좋은모델:
        칸 = [f"**{글}**" for 글 in 칸]
    줄들.append("| " + " | ".join(칸) + " |")
st.markdown("\n".join(줄들))
st.caption("굵은 줄이 검증 F2가 가장 높은 모델입니다. "
           "검증 점수만 보고 고르면 검증 데이터에 맞춘 설정이 됩니다. 교차검증 값이 함께 오르는지 봅니다.")
if 교차있음 and st.session_state.get("교차검증시간") is not None:
    st.caption(f"교차검증 F2는 훈련용 안에서 5겹으로 계산한 값입니다. 마지막 계산에 {st.session_state['교차검증시간']:.1f}초가 걸렸습니다. "
               "모델·입력·빈 값 처리·질문 횟수를 바꾸면 버튼을 다시 누릅니다. 기준값만 바꾸면 바로 다시 계산됩니다.")

기록파일 = Path("내_기록") / "최고_기록.json"      # 새로고침해도 남도록 최고 기록을 파일에 적어 둔다
if "최고기록" not in st.session_state:
    try:
        읽은것 = json.loads(기록파일.read_text(encoding="utf-8"))
        st.session_state["최고기록"] = 읽은것 if "F2" in 읽은것 else {}
    except (FileNotFoundError, ValueError, TypeError):
        st.session_state["최고기록"] = {}
최고들 = st.session_state["최고기록"]
이전 = 최고들.get("F2")
if 이전 is None or 점수(값) > 점수(이전):              # 같은 점수면 먼저 낸 기록을 남긴다
    최고들["F2"] = {"찾아낸 환자": 값["찾아낸 환자"], "안내 인원": 값["안내 인원"],
                    "모델": 좋은모델, "가중치": 내가중치, "깊이": 내깊이,
                    "기준값": 내기준, "입력": [우리말(열) for 열 in 입력열],
                    "빈 값": 결측처리, "정확도": 값["정확도"], "재현율": 값["재현율"],
                    "정밀도": 값["정밀도"], "F1": 값["F1"], "F2": 값["F2"]}
    기록파일.parent.mkdir(exist_ok=True)
    기록파일.write_text(json.dumps(최고들, ensure_ascii=False), encoding="utf-8")
최고 = 최고들.get("F2")
if 최고:
    질문글 = f" · 질문 {최고['깊이']}번" if 최고["모델"] == "질문으로 답하는 모델" else ""
    st.success(f"검증 F2 최고 기록 · {소수(최고['F2'])} · 찾아낸 환자 {최고['찾아낸 환자']}명 "
               f"(안내 {최고['안내 인원']:,}명) · {병기(최고['모델'])} · 입력 {' · '.join(최고['입력'])} · "
               f"빈 값 {빈값이름[최고['빈 값']]}{질문글} · 기준값 {최고['기준값']:.2f}")
    st.caption("최고 기록은 모델 소개 페이지에도 표시됩니다. 새로고침해도 이 브라우저에 남습니다.")

st.markdown("**기본 설정과 내 설정 · 훈련용과 검증용**")
st.caption("이 표는 로지스틱 회귀와 의사결정트리만 비교합니다.")
설정 = {"기본 설정": 기본설정, "내 설정": 내설정}
쓰임 = {"훈련용": ~검증용, "검증용": 검증용}
for 모델이름 in ("확률로 답하는 모델", "질문으로 답하는 모델"):
    st.markdown(f"**{병기(모델이름)}**")
    칸 = {}
    for 설정이름, 그설정 in 설정.items():
        for 쓰임이름, 자리 in 쓰임.items():
            TP, FN, FP, TN, 정확도, 정밀도, 재현율, F1, _ = 채점(모델이름, 그설정, 자리)
            칸[f"{설정이름} · {쓰임이름}"] = [소수(정확도), 소수(재현율), 소수(정밀도), 소수(F1),
                                              f"{TP}명", f"{FP}명"]
    실험표 = pd.DataFrame(칸, index=["정확도", "재현율", "정밀도", "F1",
                                     "찾아낸 환자 (TP)", "헛짚은 사람 (FP)"])
    실험표.index.name = ""
    st.table(실험표)

달라진것 = []
if 내가중치:
    달라진것.append("양쪽의 가중치를 같게 맞췄습니다")
if 내깊이 != 3:
    달라진것.append(f"질문 횟수를 3번에서 {내깊이}번으로 바꿨습니다")
if 내기준 != 0.50:
    달라진것.append(f"기준값을 0.50에서 {내기준:.2f}로 바꿨습니다")
if 입력열 != 기본열:
    달라진것.append("입력 속성을 바꿨습니다")
if 결측처리 != "그대로 둔다":
    달라진것.append("체질량지수가 비어 있는 사람을 지웠습니다")
st.caption("기본 설정에서 달라진 것: "
           + (" · ".join(달라진것) if 달라진것 else "없습니다."))
st.caption("훈련용은 학습에 사용한 사람들이고 검증용은 사용하지 않은 사람들입니다. "
           "질문 횟수를 늘리면 두 점수의 차이가 어떻게 달라지는지 이 표에서 확인합니다. "
           "훈련용에서만 잘 맞히는 모델은 처음 보는 사람에게 사용할 수 없습니다.")


def 파일읽기(파일):
    try:
        return json.loads(파일.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


오류말 = {"duplicate_nickname": "이미 있는 팀명입니다. 다른 팀명을 적어 주십시오.",
          "duplicate_email": "이 이메일로 이미 등록한 팀이 있습니다. 그 팀으로 이어 하려면 아래 「이미 등록한 팀으로 이어 하기」에 팀명과 열쇠를 적습니다.",
          "consent": "개인정보 수집·이용에 동의해야 등록할 수 있습니다.",
          "no_event": "행사가 아직 열리지 않았습니다. 진행자가 행사를 등록하면 됩니다.",
          "not_registered": "등록된 팀이 아니거나 열쇠가 맞지 않습니다. 팀명과 열쇠를 확인하십시오.",
          "deadline": "마감되었습니다. 더는 제출할 수 없습니다.",
          "closed": "최종 점수가 공개되어 제출이 끝났습니다.",
          "limit": "제출 상한에 닿았습니다.", "unknown_id": "test에 없는 번호가 있습니다.",
          "empty": "전화 목록이 비어 있습니다.",
          "too_few": "전화 목록은 50명 이상이어야 합니다. 기준값을 낮추면 인원이 늘어납니다.",
          "too_big": "제출 내용이 너무 큽니다. 번호는 13,020개까지 보낼 수 있습니다.",
          "network": "연결하지 못했습니다. 인터넷을 확인한 뒤 다시 누르십시오."}


def 오류글(오류):
    return 오류말.get(오류, f"처리하지 못했습니다 ({오류}). 잠시 뒤 다시 누르십시오.")


def 을를(말):
    """마지막 한글 글자에 받침이 있으면 '을', 없으면 '를'."""
    for 글자 in reversed(말):
        if "가" <= 글자 <= "힣":
            return 말 + ("을" if (ord(글자) - 0xAC00) % 28 else "를")
    return 말 + "을"


def 열쇠형식(글):
    import uuid
    try:
        return str(uuid.UUID(글.strip()))
    except (ValueError, AttributeError):
        return None


st.divider()
st.subheader("📮 인턴 등록 · 인사팀")
등록파일 = Path("내_기록") / "인턴.json"
등록 = 파일읽기(등록파일) or {}
if not isinstance(등록, dict):
    등록 = {}
등록됨 = bool(등록.get("팀명") and 등록.get("열쇠"))
if 등록됨:
    st.success(f"등록된 팀명 **{등록['팀명']}** · 소속과 성명은 센터장만 봅니다.")
    st.markdown(f"팀 열쇠 `{등록['열쇠']}`")
    st.caption("다른 컴퓨터에서 이어 하려면 이 열쇠를 적어 두십시오. 제출할 때 팀명과 함께 보내며, 열쇠가 틀리면 제출되지 않습니다.")
    if st.button("이 브라우저의 등록 정보 지우기(다른 팀이 사용할 때)"):
        등록파일.unlink(missing_ok=True)
        st.session_state.pop("전화목록", None)
        st.rerun()
else:
    if 등록.get("팀명"):
        st.warning(f"이 브라우저에는 팀명 {등록['팀명']}만 있고 열쇠가 없습니다. 아래 「이미 등록한 팀으로 이어 하기」에 열쇠를 적습니다.")
    with st.form("인턴등록"):
        칸1, 칸2 = st.columns(2)
        팀명 = 칸1.text_input("팀명 (순위판에 공개, 12자까지)", max_chars=12)
        소속 = 칸2.text_input("소속 (센터장만 봅니다)", max_chars=60)
        성명 = 칸1.text_input("성명 (센터장만 봅니다)", max_chars=30)
        이메일 = 칸2.text_input("이메일 (최종 순위 안내를 받습니다)", max_chars=80)
        동의 = st.checkbox("개인정보 수집·이용에 동의합니다")
        st.caption("수집 항목 소속·성명·이메일 · 목적 최종 순위 안내와 연락 · 보유 기간 행사 종료 후 30일 이내 파기 · "
                   "동의하지 않으면 등록과 제출을 할 수 없습니다. 전화번호는 받지 않습니다. "
                   "팀명은 순위판에 공개되고, 소속과 성명은 관리자 암호를 가진 진행자만 봅니다.")
        보냄 = st.form_submit_button("등록")
    if 보냄:
        if not (팀명.strip() and 소속.strip() and 성명.strip() and 이메일.strip()):
            st.warning("네 칸을 모두 적어 주십시오.")
        elif not 동의:
            st.warning("개인정보 수집·이용에 동의해야 등록할 수 있습니다.")
        else:
            try:
                결과, 오류 = 호출(챌린지설정, "stroke_challenge_register",
                                {"event": 챌린지설정["event"], "nick": 팀명.strip(), "org_": 소속.strip(),
                                 "name_": 성명.strip(), "email_": 이메일.strip(), "consent_": True})
            except ModuleNotFoundError:
                결과, 오류 = None, "브라우저용 실습실 주소에서만 등록할 수 있습니다"
            if 오류:
                st.error(오류글(오류))
            elif not (isinstance(결과, dict) and 결과.get("token")):
                st.error(오류글("열쇠를 받지 못했습니다"))
            else:
                등록파일.parent.mkdir(exist_ok=True)
                등록파일.write_text(json.dumps({"팀명": 결과.get("nickname") or 팀명.strip(), "열쇠": 결과["token"]},
                                               ensure_ascii=False), encoding="utf-8")
                st.rerun()
    with st.expander("이미 등록한 팀으로 이어 하기"):
        with st.form("이어하기"):
            잇는팀명 = st.text_input("팀명", max_chars=12)
            잇는열쇠 = st.text_input("팀 열쇠", placeholder="등록할 때 받은 열쇠(예: 1b4e28ba-2fa1-11d2-883f-0016d3cca427)")
            이음 = st.form_submit_button("이 팀으로 이어 하기")
        if 이음:
            열쇠 = 열쇠형식(잇는열쇠)
            if not 잇는팀명.strip() or 열쇠 is None:
                st.warning("팀명과 열쇠를 정확히 적어 주십시오. 열쇠는 하이픈(-)이 네 개 들어간 36자입니다.")
            else:
                등록파일.parent.mkdir(exist_ok=True)
                등록파일.write_text(json.dumps({"팀명": 잇는팀명.strip(), "열쇠": 열쇠}, ensure_ascii=False),
                                   encoding="utf-8")
                st.rerun()
        st.caption("팀명과 열쇠가 맞는지는 제출할 때 확인합니다. 맞지 않으면 제출되지 않습니다.")

st.divider()
st.subheader("📤 전화 목록 제출")
제출파일 = Path("내_기록") / "제출.json"
순위판주소 = "../"                                      # 실습실(app/)의 한 단계 위가 순위판이다


def 제출하기(번호들, 설정, 출처):
    """번호 목록을 센터장에게 보내 공개 절반의 점수를 받는다. 결과는 제출.json에 남긴다."""
    try:
        결과, 오류 = 호출(챌린지설정, "stroke_challenge_submit",
                        {"event": 챌린지설정["event"], "nick": 등록["팀명"], "token_": 등록["열쇠"],
                         "ids": [int(n) for n in 번호들], "setting_": 설정, "source_": 출처})
    except ModuleNotFoundError:
        결과, 오류 = None, "브라우저용 실습실 주소에서만 제출할 수 있습니다"
    if 오류:
        st.error(오류글(오류))
        return
    정밀도 = 결과["found"] / 결과["sent"] if 결과["sent"] else None
    재현율 = 결과["found"] / 결과["pos"] if 결과["pos"] else None
    F2 = F2계산(정밀도, 재현율)
    제출들 = 파일읽기(제출파일) or []
    제출들.append({"제출": 결과["n_sub"], "출처": 출처, "전화 인원(전체)": len(set(번호들)),
                   "공개 안내": 결과["sent"], "공개 찾은 환자": 결과["found"], "공개 F2": 소수(F2),
                   "설정": 설정.get("model", "") + (" · " + 설정["inputs"] if 설정.get("inputs") else "")})
    제출파일.parent.mkdir(exist_ok=True)
    제출파일.write_text(json.dumps(제출들, ensure_ascii=False), encoding="utf-8")
    st.success(f"### 공개 F2 {소수(F2)} · 공개 절반에서 찾아낸 환자 {결과['found']}명 / {결과['pos']}명 · 안내 {결과['sent']:,}명\n"
               f"제출 {결과['n_sub']}회 / {결과['max']}회 · 최종 절반의 점수는 센터장이 공개할 때 열립니다.")
    if F2 is not None and F2 >= 0.25:
        st.balloons()


if not 등록됨:
    st.info("먼저 인턴 등록을 합니다. 등록한 팀명과 열쇠로 제출합니다.")
else:
    전체X, 전체y, 전체중앙값 = 전체데이터(결측처리, 입력열)
    st.write(f"검증에서 앞선 {을를(병기(좋은모델))} train {len(전체X):,}명 전체로 다시 학습해 test 13,020명의 확률을 구하고, "
             f"기준값 {내기준:.2f} 이상인 사람에게 전화를 겁니다. test에서 체질량지수가 빈 사람은 train의 중앙값으로 채웁니다.")
    if st.button("이 설정으로 전화 목록 만들기", type="primary"):
        with st.spinner("train 전체로 다시 학습하고 있습니다."):
            시험 = 속성_더하기(테스트_읽기())
            Xb = 시험[입력열].copy()
            if 전체중앙값 is not None:
                Xb["bmi"] = Xb["bmi"].fillna(전체중앙값)
            학습결과 = 실험학습(좋은모델, 내가중치, 깊이값(좋은모델, 내깊이), tuple(입력열), 결측처리, "전체")
            확률 = 확률구하기(학습결과, Xb)
        st.session_state["전화목록"] = {
            "ids": [int(v) for v in 시험.loc[확률 >= 내기준, "id"]], "전체": len(시험),
            "설정": {"model": 정식이름.get(좋은모델, 좋은모델), "inputs": " · ".join(우리말(열) for 열 in 입력열),
                     "missing": 결측처리, "depth": int(내깊이),
                     "threshold": float(내기준),
                     "validation_f2": None if 값["F2"] is None else round(float(값["F2"]), 4)}}
    목록 = st.session_state.get("전화목록")
    if 목록:
        질문글 = f" · 질문 {목록['설정']['depth']}번" if 목록["설정"]["model"] == "의사결정트리" else ""
        st.write(f"전화를 걸 사람 **{len(목록['ids']):,}명** / {목록.get('전체', 13020):,}명 · {목록['설정']['model']} · "
                 f"입력 {목록['설정']['inputs']}{질문글} · 기준값 {목록['설정']['threshold']:.2f}")
        if len(목록["ids"]) < 50:
            st.warning("전화 목록은 50명 이상이어야 제출할 수 있습니다. 기준값을 낮추면 인원이 늘어납니다.")
        elif st.button("이 목록 제출하기"):
            제출하기(목록["ids"], 목록["설정"], "app")
    with st.expander("외부 도구로 만든 예측 제출하기"):
        st.write("다른 도구로 만든 예측도 받습니다. sample_submission.csv 형식(id, call)으로 올립니다. call이 1인 사람에게 전화를 겁니다.")
        올린파일 = st.file_uploader("id, call 두 열의 csv", type=["csv"])
        if 올린파일 is not None:
            try:
                예측파일 = pd.read_csv(올린파일)
                시험번호 = set(int(v) for v in 테스트_읽기()["id"])
                if not {"id", "call"} <= set(예측파일.columns):
                    st.error("열 이름이 id, call이어야 합니다.")
                else:
                    번호들 = [int(v) for v in 예측파일.loc[예측파일["call"].astype(int) == 1, "id"]]
                    엉뚱 = [n for n in 번호들 if n not in 시험번호]
                    if 엉뚱:
                        st.error(f"test에 없는 번호가 {len(엉뚱)}개 있습니다. 예: {엉뚱[:5]}")
                    elif len(set(번호들)) < 50:
                        st.error(f"전화를 걸 사람이 {len(set(번호들))}명입니다. 전화 목록은 50명 이상이어야 합니다.")
                    else:
                        st.write(f"전화를 걸 사람 {len(set(번호들)):,}명")
                        if st.button("이 파일 제출하기"):
                            제출하기(번호들, {"model": "외부 예측", "inputs": "", "file": 올린파일.name[:100]}, "csv")
            except Exception as 오류:
                st.error(f"파일을 읽지 못했습니다 ({type(오류).__name__}).")

제출들 = 파일읽기(제출파일) or []
if 제출들:
    st.markdown("**이 브라우저에서 제출한 기록**")
    st.dataframe(pd.DataFrame(제출들), width="stretch", hide_index=True)
st.markdown(f"[📊 순위판 열기]({순위판주소})")
