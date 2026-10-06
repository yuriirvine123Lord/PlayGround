# Backend (scaffold de estudo — sem dinheiro real)

Este `backend/` é um **esqueleto profissional para estudo**, não um backend de
cassino real. Operação com dinheiro real no Brasil exige licença SPA/MF,
certificação RNG, KYC/AML, jogo responsável e contratos com provedores.

## Arquitetura sugerida

```
client (este front estático)
  → API Gateway (HTTPS, rate-limit, WAF/Cloudflare)
    → auth-service (JWT + refresh, KYC, +18)
    → wallet-service (ledger imutável, nunca atualiza saldo direto)
    → game-service (RNG servidor, sessões, RTP configurável e auditado)
    → admin-service (RTP, limites, autoexclusão, relatórios)
    → worker (filas de saque, webhooks PIX, alertas)
Postgres (ledger + usuários) • Redis (sessões/rate-limit) • S3 (logs)
```

## API (exemplo)

```
POST /api/auth/register {cpf, nome, nascimento, senha} → 201 + KYC pendente
POST /api/auth/login → {accessToken, refreshToken}
GET  /api/wallet/me → {saldo, bloqueado} (do ledger, não campo mutável)
POST /api/wallet/deposit/demo {valor} → crédito fictício (só demo)
POST /api/games/:id/bet {valor, params} → {resultado, payout, nonce, hash}
GET  /api/games/:id/config → {rtp, minBet, maxBet, versão} (público)
GET  /api/me/limits • POST /api/me/self-exclusion
GET  /admin/audits?jogo=&de=&até= → CSV de todas as apostas (imutável)
```

Regras inegociáveis:
- RNG no **servidor** (`crypto.randomInt`), com `seed+nonce+hash` público por aposta.
- RTP **único, versionado e visível** no front. Nada de 12% escondido.
- Ledger: `entries(id, user_id, tipo, valor, saldo_após, jogo_id, nonce, hash, created_at)`.
- Saque real só após KYC +18, limites e delay + fila manual.
- Nunca confie no saldo do front; o front é só vitrine.

## Rodar o exemplo (local, demo)

```bash
cd backend
npm install   # express, cors, helmet, jsonwebtoken
node server.example.js  # http://localhost:4000/health
```

O front deste repo continua 100% estático para o preview não quebrar.
