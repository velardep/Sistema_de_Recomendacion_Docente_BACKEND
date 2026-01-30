-- ==============================
-- SLICE 3: Recomendaciones + Acciones (Aprendizaje)
-- Tablas en español
-- ==============================

-- 1) Recomendaciones generadas por el sistema (LSTM / embeddings / LLM)
create table if not exists public.recomendaciones (
  id uuid primary key default gen_random_uuid(),
  docente_id uuid not null references auth.users(id) on delete cascade,
  conversacion_id uuid references public.conversations(id) on delete set null,
  mensaje_id uuid references public.messages(id) on delete set null,

  tipo text not null check (tipo in ('estrategia', 'recurso', 'redaccion', 'otro')),
  modelo text not null default 'mock',         -- lstm / embeddings / mlp / llm / mock
  contenido text not null,                     -- texto recomendado
  metadatos jsonb not null default '{}'::jsonb, -- scores, fuentes, parámetros, etc.

  created_at timestamptz not null default now()
);

create index if not exists idx_recomendaciones_docente_id_created_at
  on public.recomendaciones(docente_id, created_at desc);

create index if not exists idx_recomendaciones_conversacion_id
  on public.recomendaciones(conversacion_id);

-- 2) Acciones del docente sobre recomendaciones (señales para MLP)
create table if not exists public.acciones_docente (
  id uuid primary key default gen_random_uuid(),
  docente_id uuid not null references auth.users(id) on delete cascade,
  recomendacion_id uuid not null references public.recomendaciones(id) on delete cascade,

  accion text not null check (accion in ('aceptar', 'rechazar', 'editar', 'solicitar_mas_detalle', 'copiar', 'calificar')),
  valor numeric,                               -- opcional: calificación 1-5, etc.
  comentario text,                             -- opcional: por qué rechazó, qué editó
  metadatos jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

create index if not exists idx_acciones_docente_docente_id_created_at
  on public.acciones_docente(docente_id, created_at desc);

create index if not exists idx_acciones_docente_recomendacion_id
  on public.acciones_docente(recomendacion_id);

-- 3) RLS
alter table public.recomendaciones enable row level security;
alter table public.acciones_docente enable row level security;

-- 4) Policies: recomendaciones (solo dueño)
drop policy if exists "reco_select_own" on public.recomendaciones;
create policy "reco_select_own"
on public.recomendaciones for select
using (auth.uid() = docente_id);

drop policy if exists "reco_insert_own" on public.recomendaciones;
create policy "reco_insert_own"
on public.recomendaciones for insert
with check (auth.uid() = docente_id);

drop policy if exists "reco_delete_own" on public.recomendaciones;
create policy "reco_delete_own"
on public.recomendaciones for delete
using (auth.uid() = docente_id);

-- 5) Policies: acciones_docente (solo dueño + la recomendación debe ser del mismo docente)
drop policy if exists "acc_select_own" on public.acciones_docente;
create policy "acc_select_own"
on public.acciones_docente for select
using (auth.uid() = docente_id);

drop policy if exists "acc_insert_own" on public.acciones_docente;
create policy "acc_insert_own"
on public.acciones_docente for insert
with check (
  auth.uid() = docente_id
  and exists (
    select 1 from public.recomendaciones r
    where r.id = recomendacion_id
      and r.docente_id = auth.uid()
  )
);

drop policy if exists "acc_delete_own" on public.acciones_docente;
create policy "acc_delete_own"
on public.acciones_docente for delete
using (auth.uid() = docente_id);
