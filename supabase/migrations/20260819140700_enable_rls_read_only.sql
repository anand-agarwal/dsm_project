-- Dashboard visitors and the Census LLM use the public anon key.
-- They may SELECT every public table. INSERT/UPDATE/DELETE stay closed
-- for anon and authenticated. The service_role key (Studio table editor,
-- CLI, and any owner-side script) bypasses RLS and remains the write path.

do $$
declare
  r record;
begin
  for r in
    select c.relname as tablename
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind = 'r'
      and not c.relispartition
  loop
    execute format('alter table public.%I enable row level security', r.tablename);

    execute format(
      'drop policy if exists public_select_only on public.%I',
      r.tablename
    );
    execute format(
      'create policy public_select_only on public.%I
         for select
         to anon, authenticated
         using (true)',
      r.tablename
    );

    execute format(
      'revoke all on table public.%I from anon, authenticated',
      r.tablename
    );
    execute format(
      'grant select on table public.%I to anon, authenticated',
      r.tablename
    );
  end loop;
end $$;

alter default privileges in schema public
  revoke all on tables from anon, authenticated;
alter default privileges in schema public
  grant select on tables to anon, authenticated;

revoke usage, select, update on all sequences in schema public
  from anon, authenticated;
