-- TaskFlow: estrutura do banco de dados
-- Cole este script no Supabase em: SQL Editor -> New query -> Run

-- 1) Tabela de tarefas
create table if not exists public.tarefas (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null default auth.uid() references auth.users (id) on delete cascade,
    titulo        text not null check (char_length(titulo) between 1 and 200),
    descricao     text default '',
    categoria     text not null check (categoria in ('Pessoal', 'Estudos', 'Trabalho')),
    prioridade    text not null check (prioridade in ('Alta', 'Média', 'Baixa')),
    status        text not null default 'Pendente'
                  check (status in ('Pendente', 'Em andamento', 'Concluída')),
    data_entrega  date,
    criado_em     timestamptz not null default now(),
    atualizado_em timestamptz not null default now()
);

create index if not exists tarefas_user_id_idx on public.tarefas (user_id);

-- 2) Atualiza "atualizado_em" automaticamente a cada edição
create or replace function public.atualizar_data_modificacao()
returns trigger
language plpgsql
as $$
begin
    new.atualizado_em = now();
    return new;
end;
$$;

drop trigger if exists tarefas_atualizado_em on public.tarefas;
create trigger tarefas_atualizado_em
    before update on public.tarefas
    for each row execute function public.atualizar_data_modificacao();

-- 3) Row Level Security (RLS): cada usuário só enxerga e altera as próprias tarefas
alter table public.tarefas enable row level security;

drop policy if exists "Usuario ve suas tarefas" on public.tarefas;
create policy "Usuario ve suas tarefas"
    on public.tarefas for select
    to authenticated
    using (auth.uid() = user_id);

drop policy if exists "Usuario cria suas tarefas" on public.tarefas;
create policy "Usuario cria suas tarefas"
    on public.tarefas for insert
    to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "Usuario edita suas tarefas" on public.tarefas;
create policy "Usuario edita suas tarefas"
    on public.tarefas for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "Usuario exclui suas tarefas" on public.tarefas;
create policy "Usuario exclui suas tarefas"
    on public.tarefas for delete
    to authenticated
    using (auth.uid() = user_id);
