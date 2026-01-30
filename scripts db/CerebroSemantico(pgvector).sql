-- ==============================
-- SLICE 5: Cerebro semántico (pgvector)
-- Tablas en español
-- ==============================

-- 1) Extensión pgvector
create extension if not exists vector;

-- 2) Temas curriculares (prontuario pre-cargado)
create table if not exists public.temas_curriculares (
  id uuid primary key default gen_random_uuid(),
  nivel text,
  grado text,
  area text,
  tema text not null,
  descripcion text,
  metadatos jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- RLS (solo lectura para autenticados; inserción solo por admin/SQL editor)
alter table public.temas_curriculares enable row level security;

drop policy if exists "temas_select_authenticated" on public.temas_curriculares;
create policy "temas_select_authenticated"
on public.temas_curriculares for select
to authenticated
using (true);

-- 3) Embeddings (índice semántico unificado)
-- Nota: docente_id NULL = contenido global (prontuario). docente_id NO NULL = contenido privado del docente (futuro UC-2).
create table if not exists public.embeddings_texto (
  id uuid primary key default gen_random_uuid(),

  docente_id uuid references auth.users(id) on delete cascade, -- null => global
  espacio_id uuid,                                            -- futuro UC-2
  tipo_fuente text not null check (tipo_fuente in ('prontuario', 'archivo', 'pdc', 'otro')),
  fuente_id uuid,                                             -- id del tema / archivo / etc.

  texto text not null,
  embedding vector(384) not null,
  metadatos jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

create index if not exists idx_embeddings_tipo_fuente on public.embeddings_texto(tipo_fuente);
create index if not exists idx_embeddings_docente_id on public.embeddings_texto(docente_id);
create index if not exists idx_embeddings_espacio_id on public.embeddings_texto(espacio_id);

-- Índice vectorial (IVFFLAT) para búsquedas rápidas
-- OJO: requiere que el planner tenga ANALYZE y datos suficientes. Igual lo dejamos creado.
create index if not exists idx_embeddings_vector_ivfflat
on public.embeddings_texto using ivfflat (embedding vector_cosine_ops) with (lists = 100);

alter table public.embeddings_texto enable row level security;

-- Select: el usuario puede leer embeddings globales (docente_id is null) y los suyos (docente_id = auth.uid()).
drop policy if exists "emb_select_global_or_own" on public.embeddings_texto;
create policy "emb_select_global_or_own"
on public.embeddings_texto for select
using (docente_id is null or docente_id = auth.uid());

-- Insert: el usuario solo puede insertar embeddings suyos (para UC-2/UC-3 luego)
drop policy if exists "emb_insert_own" on public.embeddings_texto;
create policy "emb_insert_own"
on public.embeddings_texto for insert
with check (docente_id = auth.uid());

-- Delete: solo borrar propios
drop policy if exists "emb_delete_own" on public.embeddings_texto;
create policy "emb_delete_own"
on public.embeddings_texto for delete
using (docente_id = auth.uid());

-- 4) RPC: búsqueda semántica (cosine similarity)
create or replace function public.buscar_semantico(
  query_embedding vector(384),
  match_count int default 5,
  filtro_tipo_fuente text default null,
  filtro_espacio_id uuid default null,
  filtro_docente_id uuid default null
)
returns table (
  id uuid,
  tipo_fuente text,
  fuente_id uuid,
  texto text,
  metadatos jsonb,
  similitud float
)
language sql
stable
as $$
  select
    e.id,
    e.tipo_fuente,
    e.fuente_id,
    e.texto,
    e.metadatos,
    (1 - (e.embedding <=> query_embedding)) as similitud
  from public.embeddings_texto e
  where
    (filtro_tipo_fuente is null or e.tipo_fuente = filtro_tipo_fuente)
    and (filtro_espacio_id is null or e.espacio_id = filtro_espacio_id)
    and (
      e.docente_id is null
      or (filtro_docente_id is not null and e.docente_id = filtro_docente_id)
      or (filtro_docente_id is null and e.docente_id = auth.uid())
    )
  order by e.embedding <=> query_embedding
  limit match_count;
$$;
