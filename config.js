// 챌린지 설정 — 순위판(index.html·host.html)과 실습실(app/)이 모두 이 파일을 읽는다.
// 공개용(publishable) 키만 넣는다. secret 키는 절대 넣지 않는다.
window.CHALLENGE_CONFIG = {
  SUPABASE_URL: "https://upkakhnpvepqhsbwdyjb.supabase.co",
  SUPABASE_KEY: "sb_publishable_16HKdOESG_9U5OVNGZMeYQ_of--7oV1",
  TABLE: "stroke_challenge_log",      // schema.sql이 만드는 표. 학생 수업 표(challenge_log)와 다르다
  EVENT: "교사연수-2026",              // 행사 이름. 기록마다 저장되고 순위판은 이 행사의 기록만 읽는다
  REVEAL: false,                       // true로 바꾸면 참가자 순위판에도 최종(F2) 순위가 열린다. 마감 뒤에 바꾼다
  FORM_URL: ""                         // 모델 소개 제출 폼(구글 폼 미리 채운 주소). 비우면 제출 버튼이 나오지 않는다
};
