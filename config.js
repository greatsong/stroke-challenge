// 챌린지 설정. 순위판(index.html·host.html)과 실습실(app/)이 모두 이 파일을 읽는다.
// 공개용(publishable) 키만 넣는다. secret 키는 절대 넣지 않는다.
// 마감 시각과 최종 공개 여부는 여기가 아니라 수파베이스의 행사 줄(stroke_challenge_event)이 정한다.
// 진행자는 host.html에서 관리자 암호로 바꾼다.
window.CHALLENGE_CONFIG = {
  SUPABASE_URL: "https://upkakhnpvepqhsbwdyjb.supabase.co",
  SUPABASE_KEY: "sb_publishable_16HKdOESG_9U5OVNGZMeYQ_of--7oV1",
  EVENT: "교사연수-2026",                // 행사 이름. schema.sql로 등록한 event_id와 같아야 한다
  DATA_URL: "https://greatsong.github.io/stroke-challenge/data/"    // 실습실이 train.csv·test.csv를 읽는 폴더 주소(끝의 / 필요). data/README.md
};
