-- 행사 종료 뒤 실행하는 정리 (아직 적용하지 않았습니다)
-- 등록 화면은 "행사 종료 후 30일 이내 파기"를 약속합니다(app/pages/4_미션_제출.py).
--
-- 범위: 함수 권한 회수는 모든 행사에 적용됩니다. 진행 중인 다른 행사가 있으면 실행하지 않습니다.
-- schema.sql 을 다시 실행하면 권한이 되살아나므로 이후 다시 실행하지 않습니다.
--
-- 1단계. 공개 키로 관리자 함수와 등록 함수를 부를 수 없게 합니다. 최종 순위 안내가 끝난 뒤 실행합니다.
--        등록을 막지 않으면 파기 뒤에도 개인정보가 새로 저장됩니다.
--        host.html 은 관리자 함수 세 개를 함께 불러 하나만 실패해도 공개 순위판 갱신까지 멈춥니다.
--        이후 순위는 leaderboard.html 로 봅니다. 이미 열려 있는 host.html 은 닫습니다(화면에 명단이 남습니다).
revoke execute on function public.stroke_challenge_roster(text, text) from anon, authenticated;
revoke execute on function public.stroke_challenge_admin_board(text, text) from anon, authenticated;
revoke execute on function public.stroke_challenge_admin_info(text, text) from anon, authenticated;
revoke execute on function public.stroke_challenge_set_event(text, text, boolean, timestamptz, boolean) from anon, authenticated;
revoke execute on function public.stroke_challenge_register(text, text, text, text, text, boolean, text) from anon, authenticated;

-- 2단계. 명단을 파기합니다. 되돌릴 수 없으므로 내용을 확인한 뒤 주석을 풀어 직접 실행합니다.
--        순위판은 기록·행사 표만 읽으므로 팀 행을 지워도 유지됩니다.
-- delete from public.stroke_challenge_team where event_id = '여기에-행사-이름';

-- 되돌리기(1단계만):
--   grant execute on function public.stroke_challenge_roster(text, text) to anon, authenticated;
--   grant execute on function public.stroke_challenge_admin_board(text, text) to anon, authenticated;
--   grant execute on function public.stroke_challenge_admin_info(text, text) to anon, authenticated;
--   grant execute on function public.stroke_challenge_set_event(text, text, boolean, timestamptz, boolean) to anon, authenticated;
--   grant execute on function public.stroke_challenge_register(text, text, text, text, text, boolean, text) to anon, authenticated;
