-- ============================================================
-- DS 건강검진센터 뇌졸중 예측 챌린지 — Supabase 스키마 (캐글 방식)
--
-- 실행 순서 (SQL Editor)
--   1. 이 파일 전체를 붙여 넣고 Run.
--   2. _private/labels.sql(test 13,020명의 정답)을 붙여 넣고 Run. 이 파일은 저장소에 없다.
--   3. 행사 줄을 넣는다. 아래 「행사 등록」 참고. 관리자 암호를 여기서 정한다.
--
-- 구조
--   stroke_challenge_labels  test의 정답과 공개/최종 구분. 아무도 직접 읽지 못한다(함수만 읽는다).
--   stroke_challenge_event   행사 이름·마감·최종 공개 여부·제출 상한·관리자 암호.
--   stroke_challenge_team    인턴 등록(팀명·소속·성명·이메일·팀 열쇠). 넣을 수는 있지만 읽지 못한다.
--   stroke_challenge_log     제출 기록. 공개 점수와 최종 점수를 함께 저장하되 최종은 공개 전까지 숨긴다.
--   함수                       register(등록, 팀 열쇠를 돌려준다), submit(제출·채점, 팀명과 열쇠로 확인),
--                              board(순위판), event_info(행사 정보), roster·admin_board·admin_info·set_event(관리자)
-- 관리자 암호는 crypt(암호, gen_salt('bf'))로 저장하고 crypt(넣은 암호, 저장값)으로 비교한다.
-- 공개 키(anon)는 표를 직접 읽거나 쓰지 못하고 함수만 부른다.
-- ============================================================

create extension if not exists pgcrypto;

-- 정답 ---------------------------------------------------------
create table if not exists public.stroke_challenge_labels (
  id      integer primary key,
  stroke  integer not null check (stroke in (0, 1)),
  part    text not null check (part in ('public', 'private'))
);
alter table public.stroke_challenge_labels enable row level security;   -- 정책 없음 = 아무도 못 읽는다

-- 행사 ---------------------------------------------------------
create table if not exists public.stroke_challenge_event (
  event_id         text primary key check (char_length(event_id) between 1 and 40),
  title            text not null default 'DS 건강검진센터 인턴 미션',
  deadline         timestamptz,                        -- null이면 마감 없음
  revealed         boolean not null default false,     -- true면 최종 점수가 순위판에 열린다
  max_submissions  integer not null default 40,        -- 팀당 제출 상한
  admin_pass       text not null                       -- host.html에서 넣는 암호의 crypt 해시(bf). 평문을 넣지 않는다
);
alter table public.stroke_challenge_event enable row level security;

-- 인턴 등록(개인정보) --------------------------------------------
create table if not exists public.stroke_challenge_team (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  event_id    text not null references public.stroke_challenge_event (event_id),
  nickname    text not null check (char_length(nickname) between 1 and 12),
  org         text not null check (char_length(org) between 1 and 60),
  name        text not null check (char_length(name) between 1 and 30),
  email       text not null check (email ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
  consent     boolean not null check (consent = true),
  token       uuid not null default gen_random_uuid(),   -- 팀 열쇠. 제출할 때 팀명과 함께 보낸다
  constraint stroke_challenge_team_nick_uq  unique (event_id, nickname),
  constraint stroke_challenge_team_email_uq unique (event_id, email)
);
-- 전에 만든 표에도 열쇠와 이메일 중복 금지를 더한다(처음 만드는 경우에는 아무 일도 하지 않는다)
alter table public.stroke_challenge_team add column if not exists token uuid not null default gen_random_uuid();
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'stroke_challenge_team_email_uq') then
    alter table public.stroke_challenge_team add constraint stroke_challenge_team_email_uq unique (event_id, email);
  end if;
end $$;
alter table public.stroke_challenge_team enable row level security;

-- 제출 기록 -----------------------------------------------------
create table if not exists public.stroke_challenge_log (
  id             uuid primary key default gen_random_uuid(),
  created_at     timestamptz not null default now(),
  event_id       text not null references public.stroke_challenge_event (event_id),
  nickname       text not null,
  source         text not null default 'app' check (source in ('app', 'csv')),   -- 실습실 모델 / 외부 예측 파일
  setting        jsonb not null default '{}'::jsonb,   -- 모델 이름·입력·질문 횟수·기준값·빈 값 처리
  n_called       integer not null,                     -- 제출한 번호 수(전체 test 기준)
  sent_public    integer not null,  found_public  integer not null,
  sent_private   integer not null,  found_private integer not null
);
create index if not exists stroke_challenge_log_event_idx on public.stroke_challenge_log (event_id, created_at);
alter table public.stroke_challenge_log enable row level security;

-- ============================================================
-- 함수. 모두 security definer라 표를 읽을 수 있고, 공개 키는 함수만 부른다.
-- ============================================================

-- 행사 정보(누구나) ------------------------------------------------
create or replace function public.stroke_challenge_event_info(event text)
returns table (event_id text, title text, deadline timestamptz, revealed boolean, max_submissions integer,
               n_public integer, pos_public integer, n_private integer, pos_private integer)
language sql security definer set search_path = public, extensions stable as $$
  select e.event_id, e.title, e.deadline, e.revealed, e.max_submissions,
         (select count(*)::int from stroke_challenge_labels where part = 'public'),
         (select count(*)::int from stroke_challenge_labels where part = 'public' and stroke = 1),
         (select count(*)::int from stroke_challenge_labels where part = 'private'),
         case when e.revealed then (select count(*)::int from stroke_challenge_labels where part = 'private' and stroke = 1) end
  from stroke_challenge_event e where e.event_id = event
$$;

-- 인턴 등록(누구나 넣기만) --------------------------------------------
create or replace function public.stroke_challenge_register(event text, nick text, org_ text, name_ text, email_ text, consent_ boolean)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare tok uuid; cname text;
begin
  if not exists (select 1 from stroke_challenge_event e where e.event_id = event) then
    raise exception 'no_event';
  end if;
  if consent_ is not true then raise exception 'consent'; end if;
  insert into stroke_challenge_team (event_id, nickname, org, name, email, consent)
  values (event, btrim(nick), btrim(org_), btrim(name_), lower(btrim(email_)), true)
  returning token into tok;
  return jsonb_build_object('ok', true, 'nickname', btrim(nick), 'token', tok);
exception when unique_violation then
  get stacked diagnostics cname = constraint_name;
  if cname = 'stroke_challenge_team_email_uq' then raise exception 'duplicate_email'; end if;
  raise exception 'duplicate_nickname';
end $$;

-- 제출과 채점(누구나, 등록한 팀만) -----------------------------------------
drop function if exists public.stroke_challenge_submit(text, text, integer[], jsonb, text);   -- 열쇠 인자가 없던 옛 판
create or replace function public.stroke_challenge_submit(event text, nick text, token_ uuid, ids integer[], setting_ jsonb default '{}'::jsonb, source_ text default 'app')
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare
  ev stroke_challenge_event%rowtype;
  n_sub integer; bad integer;
  s_pub integer; f_pub integer; s_pri integer; f_pri integer; pos_pub integer;
begin
  nick := btrim(nick);
  select * into ev from stroke_challenge_event e where e.event_id = event;
  if not found then raise exception 'no_event'; end if;
  if ev.revealed then raise exception 'closed'; end if;
  if ev.deadline is not null and now() > ev.deadline then raise exception 'deadline'; end if;
  if token_ is null or not exists (select 1 from stroke_challenge_team t
                 where t.event_id = event and t.nickname = nick and t.token = token_) then
    raise exception 'not_registered';
  end if;
  if ids is null or array_length(ids, 1) is null then raise exception 'empty'; end if;
  if array_length(ids, 1) > 13020 or pg_column_size(setting_) > 4000 then raise exception 'too_big'; end if;
  if (select count(distinct x) from unnest(ids) x) < 50 then raise exception 'too_few'; end if;
  -- 같은 팀이 동시에 여러 번 눌러도 상한을 넘지 않도록 팀마다 차례로 처리한다
  perform pg_advisory_xact_lock(hashtext(event || '/' || nick));
  select count(*) into n_sub from stroke_challenge_log l where l.event_id = event and l.nickname = nick;
  if n_sub >= ev.max_submissions then raise exception 'limit'; end if;

  select count(*) into bad from (select distinct unnest(ids) as id) u
   where not exists (select 1 from stroke_challenge_labels b where b.id = u.id);
  if bad > 0 then raise exception 'unknown_id'; end if;

  select count(*) filter (where b.part = 'public'),
         count(*) filter (where b.part = 'public' and b.stroke = 1),
         count(*) filter (where b.part = 'private'),
         count(*) filter (where b.part = 'private' and b.stroke = 1)
    into s_pub, f_pub, s_pri, f_pri
    from (select distinct unnest(ids) as id) u join stroke_challenge_labels b on b.id = u.id;
  select count(*) into pos_pub from stroke_challenge_labels where part = 'public' and stroke = 1;

  insert into stroke_challenge_log (event_id, nickname, source, setting, n_called, sent_public, found_public, sent_private, found_private)
  values (event, nick, source_, coalesce(setting_, '{}'::jsonb), (select count(distinct x) from unnest(ids) x), s_pub, f_pub, s_pri, f_pri);

  return jsonb_build_object('sent', s_pub, 'found', f_pub, 'pos', pos_pub,
                            'n_sub', n_sub + 1, 'max', ev.max_submissions);
end $$;

-- 순위판(누구나). 최종 점수는 revealed일 때만 채워진다 ---------------------
create or replace function public.stroke_challenge_board(event text)
returns table (nickname text, created_at timestamptz, source text, model text,
               sent integer, found integer, sent_private integer, found_private integer)
language sql security definer set search_path = public, extensions stable as $$
  select l.nickname, l.created_at, l.source, l.setting->>'model',
         l.sent_public, l.found_public,
         case when e.revealed then l.sent_private end,
         case when e.revealed then l.found_private end
  from stroke_challenge_log l join stroke_challenge_event e on e.event_id = l.event_id
  where l.event_id = event
  order by l.created_at
$$;

-- 관리자: 명단 -------------------------------------------------------
create or replace function public.stroke_challenge_roster(pass text, event text)
returns table (nickname text, org text, name text, email text, created_at timestamptz)
language sql security definer set search_path = public, extensions stable as $$
  select t.nickname, t.org, t.name, t.email, t.created_at
  from stroke_challenge_team t join stroke_challenge_event e on e.event_id = t.event_id
  where t.event_id = event and e.admin_pass = crypt(pass, e.admin_pass)
  order by t.created_at
$$;

-- 관리자: 설정과 최종 점수까지 든 기록 ------------------------------------
create or replace function public.stroke_challenge_admin_board(pass text, event text)
returns table (nickname text, created_at timestamptz, source text, setting jsonb, n_called integer,
               sent integer, found integer, sent_private integer, found_private integer)
language sql security definer set search_path = public, extensions stable as $$
  select l.nickname, l.created_at, l.source, l.setting, l.n_called,
         l.sent_public, l.found_public, l.sent_private, l.found_private
  from stroke_challenge_log l join stroke_challenge_event e on e.event_id = l.event_id
  where l.event_id = event and e.admin_pass = crypt(pass, e.admin_pass)
  order by l.created_at
$$;

-- 관리자: 행사 정보와 최종 절반의 환자 수(공개 전에도). 진행자 화면이 최종 F2를 계산할 때 쓴다 ----
create or replace function public.stroke_challenge_admin_info(pass text, event text)
returns table (event_id text, title text, deadline timestamptz, revealed boolean, max_submissions integer,
               n_public integer, pos_public integer, n_private integer, pos_private integer)
language sql security definer set search_path = public, extensions stable as $$
  select e.event_id, e.title, e.deadline, e.revealed, e.max_submissions,
         (select count(*)::int from stroke_challenge_labels where part = 'public'),
         (select count(*)::int from stroke_challenge_labels where part = 'public' and stroke = 1),
         (select count(*)::int from stroke_challenge_labels where part = 'private'),
         (select count(*)::int from stroke_challenge_labels where part = 'private' and stroke = 1)
  from stroke_challenge_event e where e.event_id = event and e.admin_pass = crypt(pass, e.admin_pass)
$$;

-- 관리자: 최종 점수 공개·마감 바꾸기(host.html에서 암호로) -----------------------
create or replace function public.stroke_challenge_set_event(pass text, event text, revealed_ boolean default null, deadline_ timestamptz default null, clear_deadline boolean default false)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare ev stroke_challenge_event%rowtype;
begin
  select * into ev from stroke_challenge_event e where e.event_id = event and e.admin_pass = crypt(pass, e.admin_pass);
  if not found then raise exception 'bad_pass'; end if;
  update stroke_challenge_event e
     set revealed = coalesce(revealed_, e.revealed),
         deadline = case when clear_deadline then null else coalesce(deadline_, e.deadline) end
   where e.event_id = event;
  return (select jsonb_build_object('revealed', e.revealed, 'deadline', e.deadline) from stroke_challenge_event e where e.event_id = event);
end $$;

revoke all on function public.stroke_challenge_event_info(text) from public;
revoke all on function public.stroke_challenge_register(text, text, text, text, text, boolean) from public;
revoke all on function public.stroke_challenge_submit(text, text, uuid, integer[], jsonb, text) from public;
revoke all on function public.stroke_challenge_board(text) from public;
revoke all on function public.stroke_challenge_roster(text, text) from public;
revoke all on function public.stroke_challenge_admin_board(text, text) from public;
revoke all on function public.stroke_challenge_admin_info(text, text) from public;
revoke all on function public.stroke_challenge_set_event(text, text, boolean, timestamptz, boolean) from public;
grant execute on function public.stroke_challenge_event_info(text) to anon, authenticated;
grant execute on function public.stroke_challenge_register(text, text, text, text, text, boolean) to anon, authenticated;
grant execute on function public.stroke_challenge_submit(text, text, uuid, integer[], jsonb, text) to anon, authenticated;
grant execute on function public.stroke_challenge_board(text) to anon, authenticated;
grant execute on function public.stroke_challenge_roster(text, text) to anon, authenticated;
grant execute on function public.stroke_challenge_admin_board(text, text) to anon, authenticated;
grant execute on function public.stroke_challenge_admin_info(text, text) to anon, authenticated;
grant execute on function public.stroke_challenge_set_event(text, text, boolean, timestamptz, boolean) to anon, authenticated;

-- 표는 함수로만 다룬다. RLS에 더해 공개 키의 표 권한도 걷어 낸다
revoke all on table public.stroke_challenge_labels from anon, authenticated;
revoke all on table public.stroke_challenge_event  from anon, authenticated;
revoke all on table public.stroke_challenge_team   from anon, authenticated;
revoke all on table public.stroke_challenge_log    from anon, authenticated;

-- ============================================================
-- 행사 등록 (값을 바꿔서 실행. 관리자 암호는 길고 짐작하기 어렵게)
-- ============================================================
-- 관리자 암호는 crypt로 해시해 저장한다(평문으로 넣으면 host.html에서 암호가 맞지 않는다).
-- insert into public.stroke_challenge_event (event_id, title, deadline, max_submissions, admin_pass)
-- values ('교사연수-2026', 'DS 건강검진센터 인턴 미션', '2026-10-15 18:00:00+09', 40,
--         crypt('여기에-관리자-암호', gen_salt('bf')));
-- 암호 바꾸기:     update public.stroke_challenge_event set admin_pass = crypt('새-암호', gen_salt('bf')) where event_id = '교사연수-2026';
--
-- 최종 점수 공개:   update public.stroke_challenge_event set revealed = true where event_id = '교사연수-2026';
-- 행사 뒤 개인정보 파기(동의서에 적은 기한 안에):
--   delete from public.stroke_challenge_team where event_id = '교사연수-2026';
--   delete from public.stroke_challenge_log  where event_id = '교사연수-2026';
