# Integração de jogos — Referencial técnico (educacional)

> Este documento é meramente informativo para fins de estudo. 
> Não integra com provedores reais aqui. Só estrutura para quando tiver licença/agregador.

## Padrões comuns (Game Aggregator / Direct Provider)

- **Launch por URL/iframe**: maioria usa `launch_url` retornado por `POST /game_launch` com `user_code`, `game_code`, `provider`, `lang`, `currency`, `return_url`.
- **Feed unificado**: `GET /games` ou feed estático com `id`, `game_code`, `provider_code`, `categories`, `rtp`, `launch_url`, `thumb`.
- **Wallet**: `seamless wallet` (transfer interno) ou `redirect wallet` (callback). Para demo: `wallet_entries` imutável (ledger).
- **Sessão/RNG**: resultados e apostas validados no servidor com `nonce + hash + server_seed`.
- **Callback/webhook**: notifica resultados/estados (payout, bet, rollback). Validar assinatura.
- **RTP configurável e versionado**: `game_configs(jogo_id, rtp, versao, ativo)` exposto ao público.

## Endpoints típicos

```
POST /api/game_launch
  { agentToken, secretKey, user_code, game_code, provider_code, user_balance, lang, currency, device }
→ { status, launch_url, session_id, ... }

GET  /api/games  (ou feed JSON)
  filtros: provider, category, lang, currency
→ lista com metadados

POST /api/bet/callback  (webhook agregador) — validar assinatura
GET  /api/wallet/balance
```

## Front (este projeto)

- `games.json` — feed com `id, nome, provedor, rtp, categorias, launch, thumb` (pronto para virar feed do agregador).
- `index.html?jogo=<id>` — abre jogo original demo. Troque `launch` por `launch_url` real.
- Cartazes SVG originais 2026 em `*.svg`.

## Back (este projeto)

- `backend/schema.sql` — ledger + configs + KYC + autoexclusão.
- `backend/server.example.js` — demo com RNG servidor + nonce/hash.
- `backend/README.md` — regras inegociáveis.

## Checklist ao conectar (quando licenciado)

- [ ] Feed oficial (lista jogos + códigos + RTP)
- [ ] Game launch via URL/iframe retornado pela API
- [ ] Wallet transfer/callback documentado
- [ ] Webhook com verificação HMAC
- [ ] Conciliação de apostas (ledger vs provedor)
- [ ] RTP auditável e visível
- [ ] KYC/+18 + autoexclusão + limites

**Nunca**: copiar cartazes/posters de terceiros. Só usar assets licenciados.
