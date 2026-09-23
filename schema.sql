-- ============================================================
-- 뇌졸중 예측 챌린지 — Supabase 스키마 (독립 실행본)
-- SQL Editor에 전체 붙여넣고 Run. 한 표로 여러 행사를 치른다(event_id로 구분).
-- 원칙: 누구나 읽고(select) 새로 쓸(insert) 수 있지만 수정·삭제는 전면 차단.
-- 이름·소속은 받지 않는다. 팀명(nickname)과 행사 이름(event_id)만 받는다.
-- ============================================================

create extension if not exists pgcrypto;

create table if not exists public.stroke_challenge_log (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  event_id      text not null check (char_length(event_id) between 1 and 40),   -- config.js의 EVENT
  nickname      text not null check (char_length(nickname) between 1 and 12),   -- 팀명

  -- 참가자가 고른 설정
  model         text not null check (char_length(model) between 1 and 40),
  inputs        text not null check (char_length(inputs) between 1 and 80),
  missing       text not null check (missing in ('그대로 둔다', '지운다')),
  weighted      boolean not null,
  depth         integer not null check (depth between 1 and 10),
  threshold     numeric(4,2) not null check (threshold between 0 and 1),

  -- 테스트 데이터에서의 결과
  accuracy      numeric(6,4),
  sent          integer not null check (sent >= 0),      -- 안내 인원 (TP + FP)
  found         integer not null check (found >= 0),     -- 찾아낸 환자 (TP)
  recall        numeric(6,4),
  precision     numeric(6,4),
  f1            numeric(6,4),
  within_quota  boolean not null,                         -- 안내 인원이 정원(config.js의 QUOTA) 이하인가
  goal          text not null default '정원'
                check (goal in ('정확도', '재현율', '정밀도', 'F1', '정원'))
);

create index if not exists stroke_challenge_log_event_idx   on public.stroke_challenge_log (event_id);
create index if not exists stroke_challenge_log_created_idx on public.stroke_challenge_log (created_at);

alter table public.stroke_challenge_log enable row level security;

create policy "stroke_challenge_public_select" on public.stroke_challenge_log
  for select using (true);

create policy "stroke_challenge_public_insert" on public.stroke_challenge_log
  for insert with check (true);

-- 행사가 끝난 뒤 정리할 때 (SQL Editor에서 진행자가 직접 실행)
--   delete from public.stroke_challenge_log where event_id = '교사연수-2026';
