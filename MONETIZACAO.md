# COLD SHOT — Monetização real (Google Play Billing)

O app Android vende **diamantes 💎 com dinheiro real** via **Google Play Billing**
(o pagamento é processado pelo Google Pay dentro da Play Store).

## 1. Produtos (criar iguais no Play Console)

| Product ID (exato) | Diamantes | Preço sugerido | Tipo |
|---|---|---|---|
| `diamantes_100` | 100💎 | R$ 4,99 | Consumível (inapp) |
| `diamantes_550` | 550💎 | R$ 19,99 | Consumível (inapp) |
| `diamantes_1200` | 1200💎 | R$ 39,99 | Consumível (inapp) |
| `diamantes_3000` | 3000💎 | R$ 89,99 | Consumível (inapp) |

## 2. Passo a passo (Play Console)

1. Crie a conta de desenvolvedor + perfil de **pagamentos** (merchant).
2. Crie o app com o package **`com.coldshot.game`** e suba o `app-debug.apk`
   (ou gere o bundle release assinado: `gradlew bundleRelease`).
3. Em **Monetizar > Produtos > Compras no app**, crie os 4 IDs acima
   como **produto gerenciado consumível**, com os preços por país.
4. Adicione **testadores de licença** (Gmail) em
   Configuração > Teste de licença + faixa de **teste interno/fechado**.
5. Instale a versão de teste no celular logado com a conta testadora e
   compre um pack: os 💎 caem na hora no saldo do jogo.

> Dica: antes de publicar os produtos, use os SKUs reservados de teste
> (`android.test.purchased`) para validar o fluxo ponta a ponta.

## 3. Como o código funciona

- `MainActivity.kt` abre o fluxo nativo (`launchBillingFlow`), **consome**
  (`consumeAsync`, pois diamante é consumível) e chama o JS
  `window.__cs_grantDiamonds(qtd)` via `evaluateJavascript`.
- `index.html` → tela **💎 COMPRAR DIAMANTES (R$)** (`PACKS`, `renderDia`,
  `buyPack`) usa `window.Android.buyDiamonds(sku)` quando roda no APK;
  no navegador mostra orientação para instalar o app.
- Catálogo espelhado em dois lugares (manter sincronizado):
  `PACK_QTY` (Kotlin) e `PACKS` (JS).

## 4. Endurecimento p/ produção

- Validar o `purchaseToken` no **servidor** via Play Developer API antes de
  creditar (hoje o crédito é client-side, ideal p/ MVP/teste).
- Assinar o app com keystore próprio e publicar via **App Bundle (.aab)**.
- Preencher **Declaração de conteúdo**, classificação etária e política de
  privacidade na ficha da loja.
