# 검진 기록 데이터 출처

`stroke_43400.csv` · 43,400명 · 열 12개(id, gender, age, hypertension, heart_disease, ever_married, work_type, Residence_type, avg_glucose_level, bmi, smoking_status, stroke) · 뇌졸중 783명(1.80%).

- 원 출처: McKinsey & Company가 Analytics Vidhya에서 연 온라인 해커톤 「Healthcare Analytics」(2018)의 훈련 파일 `train_2v.csv`. 게시자는 원자료 출처를 밝히지 않았고 "교육 목적으로만" 사용하도록 했습니다.
- 널리 알려진 캐글 「Stroke Prediction Dataset」(fedesoriano, 2021, 5,110명)은 이 파일의 부분집합입니다. 5,110명의 id·나이·성별·뇌졸중 여부가 이 파일과 모두 일치하며, 뇌졸중 비율이 4.87%로 원본(1.80%)보다 높게 뽑혀 있습니다.
- 이 저장소의 사본은 공개 저장소 [mpavlenk/Prediction-of-Stroke](https://github.com/mpavlenk/Prediction-of-Stroke)의 `train_2v.csv`를 그대로 옮긴 것입니다(2026-09-23). 참고: [Predicting Stroke from Electronic Health Records (arXiv 1904.11280)](https://arxiv.org/abs/1904.11280).

## 사용 조건

교육 목적으로만 사용합니다. 공개 대회나 상업적 용도에 쓰지 않습니다. 이름·생년월일이 없어 개인을 식별할 수는 없지만, 출처를 알 수 없는 데이터로 얻은 결과를 실제 의학적 판단에 사용해서는 안 됩니다.

## 빈 값

- `bmi` 1,462명 비어 있음. 실습실에서 「지운다」 또는 「훈련용 중앙값으로 채운다」를 고릅니다.
- `smoking_status` 13,292명 비어 있음(30.6%). 실습실의 「현재 흡연 여부」 속성은 값이 정확히 `smokes`인 사람만 1이고 비어 있는 사람은 0입니다. 캐글 5,110명 판의 `Unknown`이 이 빈 값에 해당합니다.

## 실습실이 쓰는 파생 속성

| 속성 | 정의 |
|---|---|
| 결혼 여부 | `ever_married == "Yes"` |
| 현재 흡연 여부 | `smoking_status == "smokes"` |
| 자영업 여부 | `work_type == "Self-employed"` |
| 성별 | `gender == "Male"`이면 1(남성), 아니면 0 |

실습실(`app/`)과 정답(서버의 `stroke_challenge_labels`, `scripts/make_split.py`로 만든다)은 같은 파생 속성 정의를 사용합니다. 정의를 바꾸면 실습실과 분할 스크립트를 함께 바꾸고 정답을 다시 만듭니다.
