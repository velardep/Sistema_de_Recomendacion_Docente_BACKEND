-- 1) Extensiones útiles (opcional, pero recomendable)
create extension if not exists "uuid-ossp";

-- 2) Tabla perfil docente (1-1 con auth.users)
create table if not exists public.docentes (
  id uuid primary key references auth.users(id) on delete cascade,
  nombres text not null,
  apellidos text not null,
  email text, -- redundante opcional (auth.users ya tiene email)
  unidad_educativa text,
  nivel text,         -- primaria/secundaria, etc.
  grado text,         -- 3ro de secundaria, etc.
  ciudad text,
  departamento text,
  preferencias jsonb not null default '{}'::jsonb, -- para señales MLP luego
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 3) Trigger para updated_at
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_docentes_updated_at on public.docentes;
create trigger trg_docentes_updated_at
before update on public.docentes
for each row execute function public.set_updated_at();

-- 4) Activar RLS
alter table public.docentes enable row level security;

-- 5) Políticas RLS (cada usuario solo ve/crea/edita su propio perfil)
drop policy if exists "docente_select_own" on public.docentes;
create policy "docente_select_own"
on public.docentes for select
using (auth.uid() = id);

drop policy if exists "docente_insert_own" on public.docentes;
create policy "docente_insert_own"
on public.docentes for insert
with check (auth.uid() = id);

drop policy if exists "docente_update_own" on public.docentes;
create policy "docente_update_own"
on public.docentes for update
using (auth.uid() = id)
with check (auth.uid() = id);
