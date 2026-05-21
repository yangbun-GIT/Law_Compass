CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS chat_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NULL,
  case_id uuid NULL,
  title text,
  status text DEFAULT 'active',
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role text NOT NULL,
  content text NOT NULL,
  intent text,
  violation_flags jsonb DEFAULT '[]'::jsonb,
  suggestions jsonb DEFAULT '[]'::jsonb,
  draft_case jsonb,
  knia_matches jsonb DEFAULT '[]'::jsonb,
  knia_primary_match jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_safety_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid,
  user_id uuid NULL,
  message_id uuid NULL,
  violation_type text,
  severity text,
  raw_text text,
  action text,
  created_at timestamp DEFAULT now()
);

ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS user_id uuid NULL;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS case_id uuid NULL;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title text;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS created_at timestamp DEFAULT now();
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT now();

ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS intent text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS violation_flags jsonb DEFAULT '[]'::jsonb;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS suggestions jsonb DEFAULT '[]'::jsonb;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS draft_case jsonb;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS knia_matches jsonb DEFAULT '[]'::jsonb;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS knia_primary_match jsonb;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_case_id ON chat_sessions(case_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_intent ON chat_messages(intent);
CREATE INDEX IF NOT EXISTS idx_chat_safety_logs_session ON chat_safety_logs(session_id);
