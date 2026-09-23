# 공용.py — 실습실 페이지들이 함께 쓰는 설정 읽기와 데이터 읽기
import json
from pathlib import Path

import pandas as pd

기본주소 = "https://greatsong.github.io/stroke-challenge/data/"


def 설정_읽기():
    """config.js의 CHALLENGE_CONFIG. 실습실 index.html이 config.json 파일로 건네준다.
    브라우저 밖(로컬 streamlit)에서는 파일이 없으므로 기본값을 쓴다."""
    기본 = {"url": "", "key": "", "event": "", "data": 기본주소, "form": ""}
    try:
        c = json.loads(Path("config.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return 기본
    return {"url": str(c.get("SUPABASE_URL") or ""), "key": str(c.get("SUPABASE_KEY") or ""),
            "event": str(c.get("EVENT") or ""), "data": 폴더주소(str(c.get("DATA_URL") or 기본주소)),
            "form": str(c.get("FORM_URL") or "")}


def 폴더주소(주소):
    """DATA_URL이 파일 주소(…/data/train.csv)로 적혀 있어도 폴더 주소(…/data/)만 남긴다."""
    if not 주소.endswith("/"):
        주소 = 주소.rsplit("/", 1)[0] + "/"
    return 주소


def 속성_더하기(df):
    """글자로 적힌 열에서 예·아니요 속성을 만든다. 흡연 상태가 비어 있는 사람(약 30%)은 현재 흡연 0으로 둔다."""
    df = df.copy()
    df["married"] = (df["ever_married"] == "Yes").astype(int)
    df["smokes"] = (df["smoking_status"] == "smokes").astype(int)
    df["self_employed"] = (df["work_type"] == "Self-employed").astype(int)
    df["male"] = (df["gender"] == "Male").astype(int)
    return df


def 데이터_읽기():
    """train.csv(정답 있음, 30,380명). bmi 열의 빈 값은 그대로 빈 값으로 남는다."""
    return pd.read_csv(설정_읽기()["data"] + "train.csv", encoding="utf-8", compression=None)   # Pages가 gzip으로 보내면 브라우저가 이미 풀어 준다


def 테스트_읽기():
    """test.csv(정답 없음, 13,020명). 전화를 걸 사람을 이 안에서 고른다."""
    return pd.read_csv(설정_읽기()["data"] + "test.csv", encoding="utf-8", compression=None)


def 호출(설정, 함수, 인자, 방법="POST"):
    """수파베이스 함수(rpc)를 부른다. 브라우저에서만 동작한다. 실패하면 (None, 오류 메시지)."""
    import js                                           # 브라우저(Pyodide)에서만 있다
    요청 = js.XMLHttpRequest.new()
    주소 = 설정["url"] + "/rest/v1/rpc/" + 함수
    if 방법 == "GET":
        from urllib.parse import urlencode
        요청.open("GET", 주소 + "?" + urlencode(인자), False)
    else:
        요청.open("POST", 주소, False)
        요청.setRequestHeader("Content-Type", "application/json")
    요청.setRequestHeader("apikey", 설정["key"])
    요청.setRequestHeader("Authorization", "Bearer " + 설정["key"])
    try:
        요청.send(json.dumps(인자, ensure_ascii=False) if 방법 != "GET" else None)
    except Exception:                                   # 연결 자체가 안 된 경우(인터넷·주소 문제)
        return None, "network"
    if 요청.status == 0:                                # 브라우저가 응답을 받지 못했다
        return None, "network"
    try:
        본문 = json.loads(요청.responseText)
    except ValueError:
        본문 = {}
    if not isinstance(본문, (dict, list)):
        본문 = {}
    if 요청.status == 404:                              # 함수가 없다 = 수파베이스에 행사 준비(schema.sql)가 아직 안 되었다
        return None, "no_event"
    if 요청.status >= 300:
        if isinstance(본문, list):
            본문 = {}
        return None, str((본문 or {}).get("message") or 요청.status)
    return 본문, None


def 행사_정보(설정):
    """행사 이름·마감·최종 공개 여부·제출 상한·공개/최종 인원. 브라우저 밖이면 None."""
    try:
        줄들, 오류 = 호출(설정, "stroke_challenge_event_info", {"event": 설정["event"]}, "GET")
    except ModuleNotFoundError:
        return None
    return (줄들 or [None])[0] if not 오류 else None
