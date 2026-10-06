package com.coldshot.game

import android.annotation.SuppressLint
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ConsumeParams
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.ProductDetailsResponseListener
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.QueryProductDetailsResult
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams

/**
 * COLD SHOT — FPS tático da enseada.
 * Activity única em tela cheia que roda o jogo (Three.js) dentro de um
 * WebView com aceleração de hardware, 100% offline a partir dos assets.
 *
 * Monetização real via Google Play Billing (o pagamento é processado pelo
 * Google Pay dentro da Play Store). SKUs (configurar iguais no Play Console):
 *   diamantes_100  = 100💎 | diamantes_550  = 550💎
 *   diamantes_1200 = 1200💎 | diamantes_3000 = 3000💎
 *
 * NOTA PROFISSIONAL: a entrega dos diamantes aqui é client-side (ideal para
 * consumível simples). Para blindagem antifraude em produção, valide o
 * purchaseToken no seu servidor via Play Developer API antes de creditar.
 */
class MainActivity : AppCompatActivity(), PurchasesUpdatedListener {

    companion object {
        private const val TAG = "ColdShotBilling"

        /** Catálogo precisa espelhar os produtos criados no Play Console. */
        private val PACK_QTY = mapOf(
            "diamantes_100" to 100,
            "diamantes_550" to 550,
            "diamantes_1200" to 1200,
            "diamantes_3000" to 3000
        )
    }

    private lateinit var webView: WebView
    private lateinit var billingClient: BillingClient
    private val productDetails = mutableMapOf<String, ProductDetails>()
    private var billingReady = false

    // ------------------------------------------------------------------ ciclo
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        hideSystemUi()

        webView = WebView(this).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                mediaPlaybackRequiresUserGesture = false
                loadWithOverviewMode = true
                useWideViewPort = true
                builtInZoomControls = false
                displayZoomControls = false
                cacheMode = WebSettings.LOAD_DEFAULT
                // Jogo local: permite módulos ES (three.module.js) via file://
                allowFileAccess = true
                @Suppress("DEPRECATION")
                allowFileAccessFromFileURLs = true
                @Suppress("DEPRECATION")
                allowUniversalAccessFromFileURLs = true
            }
            isVerticalScrollBarEnabled = false
            isHorizontalScrollBarEnabled = false
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
            addJavascriptInterface(StoreBridge(), "Android")
        }
        setContentView(webView)

        setupBilling()

        if (savedInstanceState == null) {
            webView.loadUrl("file:///android_asset/www/index.html")
        } else {
            webView.restoreState(savedInstanceState)
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (::webView.isInitialized && webView.canGoBack()) webView.goBack()
                else finish()
            }
        })
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (::webView.isInitialized) webView.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        hideSystemUi()
        if (::webView.isInitialized) webView.onResume()
        if (::billingClient.isInitialized && !billingReady) billingClient.startConnection(billingListener)
    }

    override fun onPause() {
        if (::webView.isInitialized) webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        if (::billingClient.isInitialized) billingClient.endConnection()
        if (::webView.isInitialized) webView.destroy()
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemUi()
    }

    private fun hideSystemUi() {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            )
    }

    // ------------------------------------------------------------------ billing
    private val billingListener = object : BillingClientStateListener {
        override fun onBillingSetupFinished(result: BillingResult) {
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                billingReady = true
                queryPacks()
            } else {
                Log.w(TAG, "Billing indisponível: ${result.debugMessage}")
            }
        }

        override fun onBillingServiceDisconnected() {
            billingReady = false
        }
    }

    private fun setupBilling() {
        billingClient = BillingClient.newBuilder(this)
            .setListener(this)
            .enablePendingPurchases(
                PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
            )
            .build()
        billingClient.startConnection(billingListener)
    }

    private fun queryPacks() {
        val products = PACK_QTY.keys.map { sku ->
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(sku)
                .setProductType(BillingClient.ProductType.INAPP)
                .build()
        }
        val params = QueryProductDetailsParams.newBuilder().setProductList(products).build()
        billingClient.queryProductDetailsAsync(params, object : ProductDetailsResponseListener {
            override fun onProductDetailsResponse(
                result: BillingResult,
                details: QueryProductDetailsResult
            ) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    productDetails.clear()
                    details.productDetailsList.forEach { productDetails[it.productId] = it }
                    Log.i(TAG, "Packs carregados: ${productDetails.keys}")
                } else {
                    Log.w(TAG, "Falha ao listar packs: ${result.debugMessage}")
                }
            }
        })
    }

    /** Chamado pelo jogo via window.Android.buyDiamonds(sku). */
    private fun launchPackFlow(sku: String) {
        if (!billingReady) {
            billingClient.startConnection(billingListener)
            notifyStore("Loja Google Play conectando… tente de novo em segundos.")
            return
        }
        val details = productDetails[sku]
        if (details == null) {
            // Produto ainda não publicado no Play Console (ou conta sem acesso):
            // informa sem quebrar o jogo.
            notifyStore("Pack indisponível na Play Store ainda. Verifique a conta de teste.")
            return
        }
        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(
                    BillingFlowParams.ProductDetailsParams.newBuilder()
                        .setProductDetails(details)
                        .build()
                )
            ).build()
        val result = billingClient.launchBillingFlow(this, params)
        if (result.responseCode != BillingClient.BillingResponseCode.OK) {
            notifyStore("Não foi possível abrir o pagamento (${result.debugMessage}).")
        }
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: List<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            for (purchase in purchases) {
                if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                    consumeAndGrant(purchase)
                }
            }
        } else if (result.responseCode == BillingClient.BillingResponseCode.USER_CANCELED) {
            notifyStore("Compra cancelada.")
        } else if (result.responseCode == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
            // Consumível com entrega pendente: o Play reenvia no reconnect.
            notifyStore("Compra pendente detectada. Reinicie o app para concluir a entrega.")
        }
    }

    private fun consumeAndGrant(purchase: Purchase) {
        val sku = purchase.products.firstOrNull()
        val qty = PACK_QTY[sku] ?: 0
        if (qty <= 0) {
            Log.w(TAG, "SKU desconhecido: $sku")
            return
        }
        val params = ConsumeParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        billingClient.consumeAsync(params) { result, _ ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                Log.i(TAG, "Compra consumida: $sku (+$qty💎)")
                runOnUiThread {
                    if (::webView.isInitialized) {
                        webView.evaluateJavascript(
                            "window.__cs_grantDiamonds && window.__cs_grantDiamonds($qty)",
                            null
                        )
                    }
                }
            } else {
                Log.w(TAG, "Falha ao consumir $sku: ${result.debugMessage}")
                notifyStore("Pagamento recebido, entrega pendente. Reinicie o app.")
            }
        }
    }

    private fun notifyStore(message: String) {
        runOnUiThread {
            if (::webView.isInitialized) {
                val escaped = message.replace("'", "\\'")
                webView.evaluateJavascript("window.__cs_storeMsg && window.__cs_storeMsg('$escaped')", null)
            }
        }
    }

    /** Ponte JavaScript: window.Android.buyDiamonds(sku) / isStoreReady(). */
    inner class StoreBridge {
        @JavascriptInterface
        fun buyDiamonds(sku: String) {
            runOnUiThread { launchPackFlow(sku) }
        }

        @JavascriptInterface
        fun isStoreReady(): Boolean = billingReady && productDetails.isNotEmpty()
    }
}
