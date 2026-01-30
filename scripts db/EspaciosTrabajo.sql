-- =========================
-- SLICE 7: espacios
-- =========================

create table if not exists public.espacios (
  id uuid primary key default gen_random_uuid(),
  docente_id uuid not null references auth.users(id) on delete cascade,
  nombre text not null,
  nivel text,
  grado text,
  materia text,
  descripcion text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- updated_at automático (opcional pero útil)
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists trg_espacios_updated_at on public.espacios;
create trigger trg_espacios_updated_at
before update on public.espacios
for each row execute function public.set_updated_at();

alter table public.espacios enable row level security;

-- Solo el dueño ve sus espacios
drop policy if exists "espacios_select_own" on public.espacios;
create policy "espacios_select_own"
on public.espacios for select
using (docente_id = auth.uid());

-- Solo el dueño crea espacios para sí mismo
drop policy if exists "espacios_insert_own" on public.espacios;
create policy "espacios_insert_own"
on public.espacios for insert
with check (docente_id = auth.uid());

-- Solo el dueño actualiza
drop policy if exists "espacios_update_own" on public.espacios;
create policy "espacios_update_own"
on public.espacios for update
using (docente_id = auth.uid())
with check (docente_id = auth.uid());

-- Solo el dueño elimina
drop policy if exists "espacios_delete_own" on public.espacios;
create policy "espacios_delete_own"
on public.espacios for delete
using (docente_id = auth.uid());
