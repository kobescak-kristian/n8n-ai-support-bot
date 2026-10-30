-- Supabase setup for the n8n AI support bot.
-- Run once in the Supabase SQL Editor of the project "n8n-ai-support-bot".
-- Shape follows Supabase's LangChain quickstart (the n8n Supabase Vector
-- Store node uses that shape), with our own table and function names.
-- Made-up data only. Safe to run again.

-- 1. pgvector
create extension if not exists vector with schema extensions;

-- 2. Knowledge-base chunks (OpenAI text-embedding-3-small = 1536 dimensions)
create table if not exists public.q123_kb_chunks (
  id bigserial primary key,
  content text,                          -- chunk text
  metadata jsonb,                        -- article_id, title, visibility, updated, status
  embedding extensions.vector(1536)
);

-- Row level security on, no policies: only the secret key (service_role) can read or write.
alter table public.q123_kb_chunks enable row level security;

-- 3. Similarity search used by the n8n node (Query Name = q123_match_chunks)
create or replace function public.q123_match_chunks (
  query_embedding extensions.vector(1536),
  match_count int default null,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
set search_path = public, extensions
as $$
begin
  return query
  select
    c.id,
    c.content,
    c.metadata,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.q123_kb_chunks c
  where c.metadata @> filter
  order by c.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- 4. Explicit grants. New Supabase projects do not expose new tables to the
-- Data API (which n8n uses) without them (Supabase changelog 45329).
-- Only service_role (the secret key n8n holds); not anon or authenticated.
grant usage on schema public to service_role;
grant select, insert, update, delete on table public.q123_kb_chunks to service_role;
grant usage, select on sequence public.q123_kb_chunks_id_seq to service_role;
revoke all on function public.q123_match_chunks(extensions.vector, int, jsonb) from public, anon, authenticated;
grant execute on function public.q123_match_chunks(extensions.vector, int, jsonb) to service_role;

-- 5. Check: should list the table with 0 rows before the first index run.
select count(*) as chunks from public.q123_kb_chunks;
