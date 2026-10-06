-- Ledger imutável + usuários + apostas (Postgres, estudo)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpf_hash TEXT UNIQUE NOT NULL,
  nome TEXT NOT NULL,
  nascimento DATE NOT NULL,
  kyc_status TEXT NOT NULL DEFAULT 'pendente', -- pendente|aprovado|recusado
  maior_idade_ok BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE wallet_entries (
  id BIGGENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  tipo TEXT NOT NULL, -- deposito_demo|aposta|premio|saque_demo|ajuste
  valor NUMERIC(14,2) NOT NULL, -- negativo sai, positivo entra
  saldo_apos NUMERIC(14,2) NOT NULL,
  jogo_id TEXT,
  nonce TEXT,
  hash TEXT UNIQUE, -- sha256(server_seed:nonce:user_id)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON wallet_entries (user_id, id DESC);

CREATE TABLE game_configs (
  jogo_id TEXT PRIMARY KEY,
  rtp NUMERIC(5,4) NOT NULL,      -- ex: 0.9680 (público e versionado)
  versao INT NOT NULL DEFAULT 1,
  min_bet NUMERIC(10,2) NOT NULL DEFAULT 1,
  max_bet NUMERIC(10,2) NOT NULL DEFAULT 1000,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE self_exclusions (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  ate TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
