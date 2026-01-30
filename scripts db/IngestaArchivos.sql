-- =========================
-- SLICE 7.5: textos_espacio
-- =========================

create table if not exists public.textos_espacio (
  id uuid primary key default gen_random_uuid(),
  docente_id uuid not null references auth.users(id) on delete cascade,
  espacio_id uuid not null references public.espacios(id) on delete cascade,
  titulo text,
  texto text not null,
  created_at timestamptz not null default now()
);

alter table public.textos_espacio enable row level security;

drop policy if exists "textos_select_own" on public.textos_espacio;
create policy "textos_select_own"
on public.textos_espacio for select
using (docente_id = auth.uid());

drop policy if exists "textos_insert_own" on public.textos_espacio;
create policy "textos_insert_own"
on public.textos_espacio for insert
with check (docente_id = auth.uid());

drop policy if exists "textos_delete_own" on public.textos_espacio;
create policy "textos_delete_own"
on public.textos_espacio for delete
using (docente_id = auth.uid());


-- Index para acelerar filtros por espacio/docente
create index if not exists idx_embeddings_espacio_docente
on public.embeddings_texto (espacio_id, docente_id);

create index if not exists idx_embeddings_tipo_fuente
on public.embeddings_texto (tipo_fuente);


alter table public.conversations
add column if not exists espacio_id uuid references public.espacios(id) on delete set null;

create index if not exists idx_conversations_espacio
on public.conversations (espacio_id);
