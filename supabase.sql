-- 환절기 카드뉴스 도구: 기기 동기화용 테이블 (Supabase SQL Editor에서 한 번 실행)
create table if not exists public.drafts (
  user_id uuid primary key default auth.uid() references auth.users on delete cascade,
  state text,
  updated_at bigint default 0,
  photo text,
  photo_updated_at bigint default 0
);
alter table public.drafts enable row level security;
drop policy if exists "own draft" on public.drafts;
create policy "own draft" on public.drafts
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
