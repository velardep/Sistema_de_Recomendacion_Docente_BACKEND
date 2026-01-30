-- =========================
-- SLICE 2: Chat (UC-1 base)
-- =========================

-- 1) Tabla de conversaciones (chats)
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  docente_id uuid not null references auth.users(id) on delete cascade,
  titulo text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2) Tabla de mensajes
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  docente_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- 3) Trigger updated_at para conversations
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_conversations_updated_at on public.conversations;
create trigger trg_conversations_updated_at
before update on public.conversations
for each row execute function public.set_updated_at();

-- 4) Índices útiles
create index if not exists idx_conversations_docente_id_created_at
  on public.conversations(docente_id, created_at desc);

create index if not exists idx_messages_conversation_id_created_at
  on public.messages(conversation_id, created_at asc);

create index if not exists idx_messages_docente_id_created_at
  on public.messages(docente_id, created_at desc);

-- 5) RLS
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- 6) Policies: conversations (solo dueño)
drop policy if exists "conv_select_own" on public.conversations;
create policy "conv_select_own"
on public.conversations for select
using (auth.uid() = docente_id);

drop policy if exists "conv_insert_own" on public.conversations;
create policy "conv_insert_own"
on public.conversations for insert
with check (auth.uid() = docente_id);

drop policy if exists "conv_update_own" on public.conversations;
create policy "conv_update_own"
on public.conversations for update
using (auth.uid() = docente_id)
with check (auth.uid() = docente_id);

drop policy if exists "conv_delete_own" on public.conversations;
create policy "conv_delete_own"
on public.conversations for delete
using (auth.uid() = docente_id);

-- 7) Policies: messages (solo dueño, y mensaje debe pertenecer a conversación del mismo docente)
drop policy if exists "msg_select_own" on public.messages;
create policy "msg_select_own"
on public.messages for select
using (auth.uid() = docente_id);

drop policy if exists "msg_insert_own" on public.messages;
create policy "msg_insert_own"
on public.messages for insert
with check (
  auth.uid() = docente_id
  and exists (
    select 1
    from public.conversations c
    where c.id = conversation_id
      and c.docente_id = auth.uid()
  )
);

drop policy if exists "msg_delete_own" on public.messages;
create policy "msg_delete_own"
on public.messages for delete
using (auth.uid() = docente_id);
