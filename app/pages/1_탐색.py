# pages/1_탐색.py — 열 하나·열 둘을 골라 살펴보기, 나이 구간별 뇌졸중 비율, 상관 히트맵, 발견 메모
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="탐색", page_icon="🔍", layout="wide")
st.title("🔍 탐색")
st.write("모델을 만들기 전에 train 데이터를 들여다봅니다. 열을 골라 분포를 보고, 뇌졸중을 겪은 사람과 겪지 않은 사람이 어디서 다른지 찾습니다.")

from 공용 import 속성_더하기, 데이터_읽기 as 공용_데이터_읽기

열이름 = {"gender": "성별", "age": "나이", "hypertension": "고혈압", "heart_disease": "심장병",
          "ever_married": "결혼 여부", "work_type": "직업", "Residence_type": "거주 지역",
          "avg_glucose_level": "평균 혈당", "bmi": "체질량지수", "smoking_status": "흡연 상태",
          "stroke": "뇌졸중"}
숫자열 = ["age", "avg_glucose_level", "bmi"]
글자열 = ["gender", "hypertension", "heart_disease", "ever_married", "work_type",
          "Residence_type", "smoking_status"]          # 고혈압·심장병은 0과 1뿐이라 글자 열처럼 값별로 센다
고를수있는열 = 숫자열 + 글자열
빈값 = "(비어 있음)"
뇌졸중색 = {"뇌졸중 없음": "#9aa5b1", "뇌졸중 있음": "#d9480f"}


def 우리말(열):
    return 열이름.get(열, 열)


def 와과(말):
    """마지막 글자에 받침이 있으면 '과', 없으면 '와'를 붙인다."""
    끝 = ord(말[-1]) - 0xAC00
    return 말 + ("과" if 0 <= 끝 < 11172 and 끝 % 28 else "와")


@st.cache_data
def 데이터_읽기():
    df = 공용_데이터_읽기()
    df["뇌졸중"] = df["stroke"].map({1: "뇌졸중 있음", 0: "뇌졸중 없음"})
    return df


@st.cache_data
def 글자값(열):
    """글자 열의 값을 문자열로 바꾸고 빈 값은 (비어 있음)이라는 하나의 값으로 둔다."""
    칸 = 데이터_읽기()[열]
    if 열 in ("hypertension", "heart_disease"):
        return 칸.map({1: "있음(1)", 0: "없음(0)"}).fillna(빈값)
    return 칸.astype("object").where(칸.notna(), 빈값).astype(str)


@st.cache_data
def 값별_집계(열):
    """값마다 인원과 뇌졸중 비율(%)."""
    df = 데이터_읽기()
    표 = df.groupby(글자값(열))["stroke"].agg(["size", "mean"]).reset_index()
    표.columns = ["값", "사람 수", "뇌졸중 비율(%)"]
    표["뇌졸중 비율(%)"] = (표["뇌졸중 비율(%)"] * 100).round(2)
    return 표.sort_values("사람 수", ascending=False)


@st.cache_data
def 교차_집계(열1, 열2):
    """두 글자 열의 교차표(인원)와 칸마다의 뇌졸중 비율(%)."""
    df = 데이터_읽기()
    묶음 = df.groupby([글자값(열1), 글자값(열2)])["stroke"]
    인원 = 묶음.size().unstack(fill_value=0)
    비율 = (묶음.mean().unstack() * 100).round(2)
    return 인원, 비율


@st.cache_data
def 산점도_표본(열1, 열2, 개수=3000):
    df = 데이터_읽기()
    return df[[열1, 열2, "뇌졸중"]].dropna().sample(n=개수, random_state=0) \
        .sort_values("뇌졸중")                          # 뇌졸중 있음 점을 나중에 그려 위에 보이게 한다


@st.cache_data
def 나이구간_집계():
    df = 데이터_읽기()
    구간 = (df["age"] // 10 * 10).clip(upper=80).astype(int)
    표 = df.groupby(구간)["stroke"].agg(["size", "mean"]).reset_index()
    표.columns = ["구간", "사람 수", "뇌졸중 비율(%)"]
    표["나이 구간"] = 표["구간"].map(lambda a: "80세 이상" if a >= 80 else f"{a}~{a + 9}세")
    표["뇌졸중 비율(%)"] = (표["뇌졸중 비율(%)"] * 100).round(2)
    return 표


@st.cache_data
def 상관_집계():
    df = 속성_더하기(데이터_읽기())
    열들 = ["age", "avg_glucose_level", "bmi", "hypertension", "heart_disease",
            "married", "smokes", "self_employed", "male", "stroke"]
    이름 = {**열이름, "married": "결혼 여부(예=1)", "smokes": "현재 흡연 여부(예=1)",
            "self_employed": "자영업 여부(예=1)", "male": "성별(남성=1)"}
    return df[열들].corr().round(2).rename(index=이름, columns=이름)


df = 데이터_읽기()
전체비율 = df["stroke"].mean() * 100

칸1, 칸2, 칸3 = st.columns(3)
칸1.metric("전체 사람 수", f"{len(df):,}명")
칸2.metric("뇌졸중을 겪은 사람", f"{int(df['stroke'].sum()):,}명")
칸3.metric("전체 뇌졸중 비율", f"{전체비율:.2f}%")


def 비율막대(표, x, 제목):
    """값별 뇌졸중 비율 막대와 전체 비율 기준선."""
    그림 = px.bar(표, x=x, y="뇌졸중 비율(%)", text="뇌졸중 비율(%)", title=제목,
                 hover_data=["사람 수"])
    그림.add_hline(y=전체비율, line_dash="dash", line_color="#d9480f",
                  annotation_text=f"전체 {전체비율:.2f}%", annotation_position="top left")
    return 그림


# ── 1. 나이 구간별 뇌졸중 비율 ─────────────────────────────
st.subheader("1. 나이 구간별 뇌졸중 비율")
st.plotly_chart(비율막대(나이구간_집계(), "나이 구간", "10세 구간마다 뇌졸중을 겪은 사람의 비율"), width="stretch")
st.caption("구간이 올라갈 때 비율이 어떻게 달라지는지, 전체 비율 점선을 처음 넘는 구간이 어디인지 봅니다.")

# ── 2. 열 하나 고르기 ─────────────────────────────────────
st.subheader("2. 열 하나 살펴보기")
열 = st.selectbox("살펴볼 열", 고를수있는열, format_func=우리말, key="열하나")
빈개수 = int(df[열].isna().sum())
if 빈개수:
    st.caption(f"{우리말(열)} 열에는 빈 값이 {빈개수:,}개 있습니다.")

왼쪽, 오른쪽 = st.columns(2)
if 열 in 숫자열:
    with 왼쪽:
        st.plotly_chart(px.histogram(df, x=열, nbins=40, title=f"{우리말(열)} 분포",
                                     labels={열: 우리말(열), "count": "사람 수"}), width="stretch")
        st.caption("값이 어디에 몰려 있는지, 한쪽으로 길게 늘어진 꼬리가 있는지 봅니다.")
    with 오른쪽:
        st.plotly_chart(px.box(df, x="뇌졸중", y=열, color="뇌졸중", color_discrete_map=뇌졸중색,
                               title=f"뇌졸중 여부별 {우리말(열)}", labels={열: 우리말(열)}), width="stretch")
        st.caption("두 상자의 가운데 선(중앙값)과 상자 높이가 얼마나 다른지 봅니다.")
else:
    표 = 값별_집계(열)
    with 왼쪽:
        st.plotly_chart(px.bar(표, x="값", y="사람 수", text="사람 수", title=f"{우리말(열)} 값별 인원"),
                        width="stretch")
        st.caption("값마다 사람이 얼마나 있는지, 사람 수가 아주 적은 값이 있는지 봅니다.")
    with 오른쪽:
        st.plotly_chart(비율막대(표, "값", f"{우리말(열)} 값별 뇌졸중 비율"), width="stretch")
        st.caption("점선(전체 비율)보다 높은 값과 낮은 값을 찾고, 그 값의 사람 수도 함께 봅니다.")

# ── 3. 열 둘 고르기 ───────────────────────────────────────
st.subheader("3. 열 둘 함께 살펴보기")
고른1, 고른2 = st.columns(2)
열1 = 고른1.selectbox("첫째 열", 고를수있는열, index=0, format_func=우리말, key="열둘_1")
열2 = 고른2.selectbox("둘째 열", 고를수있는열, index=1, format_func=우리말, key="열둘_2")

if 열1 == 열2:
    st.info("서로 다른 두 열을 고릅니다.")
elif 열1 in 숫자열 and 열2 in 숫자열:
    표본 = 산점도_표본(열1, 열2)
    st.plotly_chart(px.scatter(표본, x=열1, y=열2, color="뇌졸중", color_discrete_map=뇌졸중색, opacity=0.6,
                               title=f"{와과(우리말(열1))} {우리말(열2)} (빈 값이 없는 사람 중 3,000명 표본)",
                               labels={열1: 우리말(열1), 열2: 우리말(열2)}), width="stretch")
    st.caption("뇌졸중 있음 점이 그림의 어느 영역에 모여 있는지 봅니다.")
else:
    if 열1 in 숫자열 or 열2 in 숫자열:
        숫자, 글자 = (열1, 열2) if 열1 in 숫자열 else (열2, 열1)
        그림표 = pd.DataFrame({우리말(글자): 글자값(글자), 우리말(숫자): df[숫자], "뇌졸중": df["뇌졸중"]})
        st.plotly_chart(px.box(그림표, x=우리말(글자), y=우리말(숫자), color="뇌졸중",
                               color_discrete_map=뇌졸중색,
                               title=f"{우리말(글자)} 값별 {우리말(숫자)} 분포 (뇌졸중 여부로 나눔)"),
                        width="stretch")
        st.caption(f"{우리말(글자)} 값마다 {우리말(숫자)}의 상자가 어떻게 다른지, 뇌졸중 여부에 따른 차이가 값마다 같은지 봅니다.")
    else:
        인원, 비율 = 교차_집계(열1, 열2)
        왼쪽, 오른쪽 = st.columns(2)
        축 = {"x": 우리말(열2), "y": 우리말(열1)}
        with 왼쪽:
            st.plotly_chart(px.imshow(인원, text_auto=True, color_continuous_scale="Blues", aspect="auto",
                                      labels={**축, "color": "사람 수"}, title="교차표 (사람 수)"),
                            width="stretch")
            st.caption("사람 수가 아주 적은 칸이 있는지 봅니다.")
        with 오른쪽:
            st.plotly_chart(px.imshow(비율, text_auto=True, color_continuous_scale="Oranges", aspect="auto",
                                      labels={**축, "color": "뇌졸중 비율(%)"},
                                      title=f"칸마다 뇌졸중 비율(%) · 전체 {전체비율:.2f}%"),
                            width="stretch")
            st.caption("비율이 높은 칸을 찾고, 왼쪽 표에서 그 칸의 사람 수를 함께 확인합니다.")

# ── 4. 상관 히트맵 ────────────────────────────────────────
st.subheader("4. 속성끼리의 상관")
st.plotly_chart(px.imshow(상관_집계(), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                          aspect="auto", title="상관계수 (예·아니요 속성은 예=1, 아니요=0)"), width="stretch")
st.caption("맨 아래 뇌졸중 줄에서 절댓값이 큰 속성과, 입력 속성끼리 서로 강하게 얽힌 쌍을 봅니다. "
           "체질량지수가 비어 있는 사람은 그 칸의 계산에서 빠집니다.")

# ── 5. 내가 발견한 것 ─────────────────────────────────────
저장파일 = Path("내_기록") / "탐색_메모.json"   # 적은 내용을 남겨 두어 새로고침해도 다시 불러온다


def 저장하기():
    """발견 메모 칸에 적은 내용을 파일에 남긴다."""
    저장파일.parent.mkdir(exist_ok=True)
    저장파일.write_text(json.dumps({"메모": st.session_state["탐색메모"]}, ensure_ascii=False),
                        encoding="utf-8")


if "탐색메모" not in st.session_state:
    try:
        st.session_state["탐색메모"] = json.loads(저장파일.read_text(encoding="utf-8")).get("메모", "")
    except (FileNotFoundError, ValueError):
        st.session_state["탐색메모"] = ""

st.subheader("5. 내가 발견한 것")
st.caption("모델의 입력으로 사용할 만한 속성과 그렇게 생각한 근거를 적습니다. "
           "적은 내용은 이 브라우저에 저장되어 새로고침해도 남습니다.")
st.text_area("발견 메모", key="탐색메모", height=180, on_change=저장하기,
             placeholder="예) ○○ 값이 △△인 사람들의 뇌졸중 비율이 전체보다 높다. 사람 수는 …명이다.")
