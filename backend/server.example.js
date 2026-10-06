// server.example.js — API demo (sem dinheiro real). Rode com: cd backend && npm install express cors helmet jsonwebtoken && node server.example.js
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import crypto from 'node:crypto';

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '20kb' }));

// Demo em memória (troque por Postgres/Redis em produção)
const balances = new Map(); // userId -> saldo fictício
const bets = [];
const GAME_RTP = { tiger: 0.968, slots777: 0.971, crash: 0.97 }; // público, versionado

function rngInt(min, max) { return crypto.randomInt(min, max + 1); }
function getUser(req) { return req.header('x-demo-user') || 'demo-user'; }

app.get('/health', (req, res) => res.json({ ok: true, demo: true }));

app.get('/api/games/:id/config', (req, res) => {
  const rtp = GAME_RTP[req.params.id] ?? 0.96;
  res.json({ jogo: req.params.id, rtp, versao: 1, minBet: 1, maxBet: 1000, moeda: 'BRL-DEMO' });
});

app.get('/api/wallet/me', (req, res) => {
  const u = getUser(req);
  res.json({ saldo: balances.get(u) ?? 1000, moeda: 'BRL-DEMO' });
});

// Aposta demo: valida, sorteia no SERVIDOR, lança no ledger em memória
app.post('/api/games/:id/bet', (req, res) => {
  const u = getUser(req);
  const valor = Math.floor(Number(req.body?.valor));
  if (!Number.isFinite(valor) || valor <= 0) return res.status(400).json({ erro: 'valor inválido' });
  const saldo = balances.get(u) ?? 1000;
  if (valor > saldo) return res.status(402).json({ erro: 'saldo demo insuficiente' });

  // Exemplo simplificado: slot 3 símbolos com RTP aproximado via tabela
  const syms = ['A', 'B', 'C', 'D'];
  const r = [syms[rngInt(0, 3)], syms[rngInt(0, 3)], syms[rngInt(0, 3)]];
  const mult = (r[0] === r[1] && r[1] === r[2]) ? 8 : (r[0] === r[1] || r[1] === r[2] ? 1 : 0);
  const payout = valor * mult;
  const nonce = crypto.randomUUID();
  const hash = crypto.createHash('sha256').update(`${nonce}:${u}:${Date.now()}`).digest('hex');

  balances.set(u, saldo - valor + payout);
  bets.unshift({ user: u, jogo: req.params.id, valor, payout, resultado: r, nonce, hash, em: new Date().toISOString() });

  res.json({ resultado: r, mult, payout, saldo: balances.get(u), nonce, hash, rtp: GAME_RTP[req.params.id] ?? 0.96 });
});

app.listen(4000, () => console.log('demo API em http://localhost:4000 (BRL-DEMO, sem dinheiro real)'));
