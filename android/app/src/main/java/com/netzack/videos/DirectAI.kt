package com.netzack.videos

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit

/**
 * Netzack Videos V2 — acesso DIRETO às IAs, sem servidor.
 * O usuário cola QUALQUER chave; o app identifica o provedor sozinho testando
 * os endpoints oficiais já embarcados (nunca exibidos na tela) e escolhe o modelo.
 */
object DirectAI {

    // ---- Provedores do mercado (URLs EMBUTIDAS, escondidas do usuário) ----
    data class Endpoint(
        val id: String,
        val name: String,
        val baseUrl: String,
        val auth: String, // "goog" | "x-api" | "bearer"
        val nativeGoogle: Boolean = false,
        val nativeAnthropic: Boolean = false
    )

    val ENDPOINTS: List<Endpoint> = listOf(
        Endpoint("google", "Google Gemini / Veo", "https://generativelanguage.googleapis.com/v1beta", "goog", nativeGoogle = true),
        Endpoint("anthropic", "Anthropic Claude", "https://api.anthropic.com/v1", "x-api", nativeAnthropic = true),
        Endpoint("openai", "OpenAI GPT / Sora", "https://api.openai.com/v1", "bearer"),
        Endpoint("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "bearer"),
        Endpoint("groq", "Groq", "https://api.groq.com/openai/v1", "bearer"),
        Endpoint("xai", "xAI Grok", "https://api.x.ai/v1", "bearer"),
        Endpoint("mistral", "Mistral", "https://api.mistral.ai/v1", "bearer"),
        Endpoint("together", "Together AI", "https://api.together.xyz/v1", "bearer"),
        Endpoint("cerebras", "Cerebras", "https://api.cerebras.ai/v1", "bearer"),
        Endpoint("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "bearer"),
        Endpoint("siliconflow", "SiliconFlow", "https://api.siliconflow.cn/v1", "bearer"),
        Endpoint("moonshot", "Moonshot Kimi", "https://api.moonshot.ai/v1", "bearer"),
        Endpoint("fireworks", "Fireworks", "https://api.fireworks.ai/inference/v1", "bearer"),
        Endpoint("gemini-oai", "Google Gemini (compat)", "https://generativelanguage.googleapis.com/v1beta/openai", "bearer"),
        Endpoint("perplexity", "Perplexity", "https://api.perplexity.ai", "bearer")
    )

    private val PREFIX_HINT = linkedMapOf(
        "AIza" to "google",
        "sk-ant-" to "anthropic",
        "gsk_" to "groq",
        "xai-" to "xai",
        "sk-or-" to "openrouter"
    )

    private val CHAT_PRIORITY = mapOf(
        "google" to listOf("gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash"),
        "gemini-oai" to listOf("gemini-3.1-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"),
        "anthropic" to listOf("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"),
        "openai" to listOf("gpt-5.5", "gpt-5", "gpt-5-mini", "gpt-4o"),
        "deepseek" to listOf("deepseek-chat", "deepseek-reasoner"),
        "groq" to listOf("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
        "xai" to listOf("grok-4", "grok-3", "grok-3-mini"),
        "mistral" to listOf("mistral-large-latest", "mistral-small-latest"),
        "together" to listOf("meta-llama/Llama-3.3-70B-Instruct-Turbo"),
        "cerebras" to listOf("llama-3.3-70b"),
        "openrouter" to listOf("openrouter/auto", "anthropic/claude-sonnet-4", "openai/gpt-4o"),
        "siliconflow" to listOf("Qwen/Qwen2.5-72B-Instruct"),
        "moonshot" to listOf("kimi-k2-0711-preview", "moonshot-v1-8k"),
        "fireworks" to listOf("accounts/fireworks/models/llama-v3p3-70b-instruct"),
        "perplexity" to listOf("sonar-pro", "sonar")
    )

    val VIDEO_PRIORITY = listOf(
        "veo-3.1-generate-preview",
        "veo-3.1-generate-001",
        "veo-3.0-generate-preview",
        "veo-3.0-generate-001",
        "veo-2.0-generate-001"
    )
    val GOOGLE_CHAT = CHAT_PRIORITY.getValue("google")

    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private val probeClient = OkHttpClient.Builder()
        .connectTimeout(6, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .writeTimeout(8, TimeUnit.SECONDS)
        .build()

    fun normalize(raw: String): String = raw.substringAfterLast("/").trim()

    /** Detecção por prefixo (rápida, sem rede). */
    fun detect(key: String): String {
        val k = key.trim()
        if (k.startsWith("AIza")) return "google"
        if (k.startsWith("sk-ant-")) return "anthropic"
        if (k.startsWith("sk-")) return "openai"
        throw IllegalArgumentException(
            "Chave não reconhecida. Cole uma chave Google (AIza…), OpenAI (sk-…) ou Anthropic (sk-ant-…)."
        )
    }

    /** Qualquer chave: testa os endpoints embarcados em ordem inteligente até achar quem aceita. */
    fun chooseEndpoint(key: String, probe: (Endpoint) -> Boolean): Endpoint? {
        val k = key.trim()
        val hinted = PREFIX_HINT.entries.firstOrNull { k.startsWith(it.key) }?.value
        val ordered = if (hinted != null) {
            ENDPOINTS.filter { it.id == hinted } + ENDPOINTS.filter { it.id != hinted }
        } else {
            ENDPOINTS
        }
        return ordered.firstOrNull { probe(it) }
    }

    fun redact(key: String): String {
        val k = key.trim()
        if (k.length <= 8) return "********"
        return "${k.take(4)}…${k.takeLast(4)}"
    }

    /** Divide a duração total em pedaços válidos (ex.: até 10 min em clips de até 8 s). */
    fun splitDuration(total: Int, allowed: Set<Int>): List<Int> {
        val sorted = allowed.sorted()
        val minA = sorted.first()
        val out = mutableListOf<Int>()
        var rem = total
        while (rem > 0 && out.size < 400) {
            val fits = sorted.filter { it <= rem }.maxOrNull()
            val take = when {
                fits == null -> sorted.first()
                rem - fits == 0 || rem - fits >= minA -> fits
                else -> sorted.firstOrNull { it >= rem } ?: fits
            }
            out += take
            rem -= take
        }
        return out
    }

    private fun authHeaders(ep: Endpoint, key: String): Map<String, String> = when (ep.auth) {
        "goog" -> mapOf("x-goog-api-key" to key)
        "x-api" -> mapOf("x-api-key" to key, "anthropic-version" to "2023-06-01")
        else -> mapOf("Authorization" to "Bearer $key")
    }

    private fun msgOf(text: String): String {
        return try {
            val obj = JSONObject(text)
            val err = obj.opt("error")
            if (err is JSONObject) {
                (err.optString("message").ifBlank { err.toString() }).take(300)
            } else {
                obj.optString("detail", text).ifBlank { text }.take(300)
            }
        } catch (_: Exception) {
            text.take(300)
        }
    }

    private fun netErr(e: Exception): RuntimeException = when (e) {
        is UnknownHostException -> RuntimeException("Falha de rede: não consegui alcançar a IA.")
        is SocketTimeoutException -> RuntimeException("A IA demorou para responder. Tente de novo.")
        else -> RuntimeException("Falha de rede com a IA. Verifique sua internet.")
    }

    private fun get(url: String, headers: Map<String, String>, short: Boolean = false): JSONObject {
        val b = Request.Builder().url(url).get()
        headers.forEach { (k, v) -> b.header(k, v) }
        val c = if (short) probeClient else client
        try {
            c.newCall(b.build()).execute().use { resp ->
                val text = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) throw RuntimeException(msgOf(text))
                return JSONObject(text)
            }
        } catch (e: RuntimeException) {
            throw e
        } catch (e: Exception) {
            throw netErr(e)
        }
    }

    private fun getRaw(url: String, headers: Map<String, String>): ByteArray {
        val b = Request.Builder().url(url).get()
        headers.forEach { (k, v) -> b.header(k, v) }
        try {
            client.newCall(b.build()).execute().use { resp ->
                if (!resp.isSuccessful) throw RuntimeException("Falha ao baixar (HTTP ${resp.code}).")
                val body = resp.body ?: throw RuntimeException("Download vazio.")
                return body.bytes()
            }
        } catch (e: RuntimeException) {
            throw e
        } catch (e: Exception) {
            throw netErr(e)
        }
    }

    private fun post(url: String, headers: Map<String, String>, body: JSONObject): JSONObject {
        val b = Request.Builder().url(url).post(body.toString().toRequestBody(JSON))
        headers.forEach { (k, v) -> b.header(k, v) }
        try {
            client.newCall(b.build()).execute().use { resp ->
                val text = resp.body?.string() ?: "{}"
                if (!resp.isSuccessful) throw RuntimeException("A IA recusou (HTTP ${resp.code}): ${msgOf(text)}")
                return JSONObject(text)
            }
        } catch (e: RuntimeException) {
            throw e
        } catch (e: Exception) {
            throw netErr(e)
        }
    }

    private fun probeEndpoint(ep: Endpoint, key: String): Boolean = try {
        get("${ep.baseUrl}/models", authHeaders(ep, key), short = true)
        true
    } catch (_: Exception) {
        false
    }

    data class Detected(val ep: Endpoint)

    /** Identifica o provedor que aceita a chave, testando os endpoints embarcados. */
    fun identify(key: String, onProgress: (Int, Int) -> Unit = { _, _ -> }): Endpoint {
        val k = key.trim()
        if (k.isBlank()) throw IllegalArgumentException("Cole sua chave API primeiro.")
        val chosen = chooseEndpoint(k) { ep ->
            val idx = ENDPOINTS.indexOf(ep) + 1
            onProgress(idx, ENDPOINTS.size)
            probeEndpoint(ep, k)
        } ?: throw IllegalArgumentException(
            "Nenhum provedor reconheceu esta chave. Cole uma chave de um provedor do mercado (Google, OpenAI, Anthropic, Groq, DeepSeek, Mistral…)."
        )
        return chosen
    }

    private val JUNK_MODEL = Regex("embedding|moderation|whisper|dall-e|tts|audio|image|rerank|guard|detranscribe|realtime|search-preview", RegexOption.IGNORE_CASE)

    fun listModels(ep: Endpoint, key: String): List<String> {
        val data = get("${ep.baseUrl}/models", authHeaders(ep, key))
        val arr = data.optJSONArray("models") ?: data.optJSONArray("data") ?: return emptyList()
        val out = mutableListOf<String>()
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            val raw = item.optString("name").ifBlank { item.optString("id") }
            if (raw.isNotBlank()) {
                val n = normalize(raw)
                if (n.isNotBlank() && n !in out) out.add(n)
            }
        }
        return out
    }

    fun pickVideoModel(models: List<String>): String {
        val norm = models.map(::normalize)
        VIDEO_PRIORITY.firstOrNull { it in norm }?.let { return it }
        if (norm.isNotEmpty()) throw RuntimeException(
            "Sua chave Google não tem nenhum modelo Veo liberado. Libere o Veo na sua conta Google para gerar vídeo (o chat funciona normal)."
        )
        return VIDEO_PRIORITY[0]
    }

    fun pickChatModel(provider: String, models: List<String>): String {
        val norm = models.map(::normalize)
        (CHAT_PRIORITY[provider] ?: emptyList()).firstOrNull { it in norm }?.let { return it }
        norm.firstOrNull { !JUNK_MODEL.containsMatchIn(it) }?.let { return it }
        if (norm.isNotEmpty()) return norm[0]
        return CHAT_PRIORITY[provider]?.firstOrNull()
            ?: throw RuntimeException("A IA não listou nenhum modelo de chat.")
    }

    data class ChatOut(val provider: String, val model: String, val text: String)

    fun chat(ep: Endpoint, key: String, prompt: String, modelHint: String? = null): ChatOut {
        val models = listModels(ep, key)
        val model = modelHint ?: pickChatModel(ep.id, models)
        val text = when {
            ep.nativeGoogle -> {
                val body = JSONObject()
                    .put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", prompt)))))
                    .put("generationConfig", JSONObject().put("temperature", 0.7))
                val res = post("${ep.baseUrl}/models/$model:generateContent", authHeaders(ep, key), body)
                val parts = res.optJSONArray("candidates")?.optJSONObject(0)?.optJSONObject("content")?.optJSONArray("parts")
                val sb = StringBuilder()
                if (parts != null) for (i in 0 until parts.length()) sb.append(parts.optJSONObject(i)?.optString("text") ?: "")
                sb.toString().trim()
            }
            ep.nativeAnthropic -> {
                val body = JSONObject()
                    .put("model", model)
                    .put("max_tokens", 4096)
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
                val res = post("${ep.baseUrl}/messages", authHeaders(ep, key), body)
                val blocks = res.optJSONArray("content")
                val sb = StringBuilder()
                if (blocks != null) for (i in 0 until blocks.length()) sb.append(blocks.optJSONObject(i)?.optString("text") ?: "")
                sb.toString().trim()
            }
            else -> {
                val body = JSONObject()
                    .put("model", model)
                    .put("temperature", 0.7)
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
                val res = post("${ep.baseUrl}/chat/completions", authHeaders(ep, key), body)
                val msg = res.optJSONArray("choices")?.optJSONObject(0)?.optJSONObject("message")
                var out = msg?.optString("content") ?: ""
                if (out.isBlank()) {
                    val r = msg?.opt("reasoning_content")
                    out = if (r is String) r else ""
                }
                out.trim()
            }
        }
        if (text.isBlank()) throw RuntimeException("A IA não devolveu texto. Tente de novo.")
        return ChatOut(ep.name, model, text)
    }

    // ---------------- VÍDEO ----------------

    val VEO_CHUNKS = setOf(4, 6, 8)
    val SORA_CHUNKS = setOf(4, 8, 12)

    /** Google Veo: inicia 1 pedaço. Retorna (modelo, operação). */
    fun startVeo(key: String, prompt: String, aspectRatio: String, resolution: String, seconds: Int, audio: Boolean, negative: String?): Pair<String, String> {
        val models = listModels(ENDPOINTS.first { it.id == "google" }, key)
        val model = pickVideoModel(models)
        val params = JSONObject()
            .put("aspectRatio", aspectRatio)
            .put("resolution", resolution)
            .put("durationSeconds", seconds)
            .put("generateAudio", audio)
            .put("sampleCount", 1)
        if (!negative.isNullOrBlank()) params.put("negativePrompt", negative)
        val body = JSONObject()
            .put("instances", JSONArray().put(JSONObject().put("prompt", prompt)))
            .put("parameters", params)
        val res = post("${ENDPOINTS.first { it.id == "google" }.baseUrl}/models/$model:predictLongRunning", authHeaders(ENDPOINTS.first { it.id == "google" }, key), body)
        var name = res.optString("name")
        if (name.isBlank()) name = res.optJSONObject("operation")?.optString("name") ?: ""
        if (name.isBlank()) throw RuntimeException("O Veo não devolveu a operação de vídeo.")
        return model to name
    }

    data class PollOut(val done: Boolean, val ref: JSONObject?)

    fun pollVeo(key: String, operation: String): PollOut {
        val google = ENDPOINTS.first { it.id == "google" }
        val url = if (operation.startsWith("http")) operation else "${google.baseUrl}/${operation.trimStart('/')}"
        val res = get(url, authHeaders(google, key))
        if (!res.optBoolean("done", false)) return PollOut(false, null)
        if (!res.isNull("error")) {
            val e = res.optJSONObject("error")
            throw RuntimeException("O Veo falhou: ${(e?.optString("message") ?: e.toString()).take(300)}")
        }
        val resp = res.optJSONObject("response") ?: JSONObject()
        val samples = resp.optJSONObject("generateVideoResponse")?.optJSONArray("generatedSamples")
        val first = samples?.optJSONObject(0)
        val video = first?.optJSONObject("video") ?: first
            ?: throw RuntimeException("O Veo terminou mas não trouxe o vídeo.")
        return PollOut(true, video)
    }

    fun downloadVeo(key: String, ref: JSONObject, dest: File) {
        val b64 = ref.optString("bytesBase64Encoded")
        if (b64.isNotBlank()) {
            dest.writeBytes(android.util.Base64.decode(b64, android.util.Base64.DEFAULT))
            return
        }
        val uri = ref.optString("uri").ifBlank { ref.optString("url") }
        if (uri.isBlank() || uri.startsWith("gs://")) throw RuntimeException(
            "O Veo devolveu um link que o app não consegue baixar direto."
        )
        dest.writeBytes(getRaw(uri, mapOf("x-goog-api-key" to key)))
    }

    // ---- OpenAI Sora (vídeo) ----

    fun startSora(key: String, prompt: String, seconds: Int, size: String): String {
        val openai = ENDPOINTS.first { it.id == "openai" }
        val variants = listOf(
            JSONObject().put("model", "sora-2").put("prompt", prompt).put("seconds", seconds.toString()).put("size", size),
            JSONObject().put("model", "sora-2").put("prompt", prompt).put("seconds", seconds).put("size", size),
            JSONObject().put("model", "sora-2").put("prompt", prompt).put("seconds", seconds.toString()),
            JSONObject().put("model", "sora-2").put("prompt", prompt)
        )
        var last: Exception? = null
        for (v in variants) {
            try {
                val res = post("${openai.baseUrl}/videos", authHeaders(openai, key), v)
                val id = res.optString("id")
                if (id.isNotBlank()) return id
            } catch (e: Exception) {
                last = e
            }
        }
        throw last ?: RuntimeException("O Sora não aceitou o pedido de vídeo.")
    }

    fun pollSora(key: String, id: String): Pair<Boolean, String?> {
        val openai = ENDPOINTS.first { it.id == "openai" }
        val res = get("${openai.baseUrl}/videos/$id", authHeaders(openai, key))
        val status = res.optString("status")
        return when (status) {
            "completed" -> true to null
            "failed", "cancelled" -> true to (res.optString("error").ifBlank { "O Sora falhou." })
            else -> false to null
        }
    }

    fun downloadSora(key: String, id: String, dest: File) {
        val openai = ENDPOINTS.first { it.id == "openai" }
        dest.writeBytes(getRaw("${openai.baseUrl}/videos/$id/content", authHeaders(openai, key)))
    }

    fun soraSize(aspectRatio: String, resolution: String): String {
        val (w, h) = when (resolution) {
            "1080p" -> 1920 to 1080
            "4k" -> 3840 to 2160
            else -> 1280 to 720
        }
        return if (aspectRatio == "9:16") "${h}x${w}" else "${w}x${h}"
    }
}
