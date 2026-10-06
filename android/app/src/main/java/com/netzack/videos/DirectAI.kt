package com.netzack.videos

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Netzack Videos V2 — acesso DIRETO às IAs, sem servidor.
 * Endpoints oficiais e prioridades de modelo já vêm embarcados:
 * é só colar a chave que o app identifica provedor + modelo sozinho.
 */
object DirectAI {

    const val GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"
    const val OPENAI_BASE = "https://api.openai.com/v1"
    const val ANTHROPIC_BASE = "https://api.anthropic.com/v1"

    val VIDEO_PRIORITY = listOf(
        "veo-3.1-generate-preview",
        "veo-3.1-generate-001",
        "veo-3.0-generate-preview",
        "veo-3.0-generate-001",
        "veo-2.0-generate-001"
    )
    val GOOGLE_CHAT = listOf(
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash"
    )
    val OPENAI_CHAT = listOf("gpt-5.5", "gpt-5", "gpt-5-mini", "gpt-4o")
    val ANTHROPIC_CHAT = listOf(
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5"
    )

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    fun normalize(raw: String): String = raw.substringAfterLast("/").trim()

    /** Só a chave basta: AIza… = Google, sk-ant-… = Anthropic, sk-… = OpenAI. */
    fun detect(key: String): String {
        val k = key.trim()
        if (k.startsWith("AIza")) return "google"
        if (k.startsWith("sk-ant-")) return "anthropic"
        if (k.startsWith("sk-")) return "openai"
        throw IllegalArgumentException(
            "Chave não reconhecida. Cole uma chave Google (AIza…), OpenAI (sk-…) ou Anthropic (sk-ant-…)."
        )
    }

    fun redact(key: String): String {
        val k = key.trim()
        if (k.length <= 8) return "********"
        return "${k.take(4)}…${k.takeLast(4)}"
    }

    private fun errMsg(text: String): String {
        return try {
            val obj = JSONObject(text)
            val err = obj.opt("error")
            if (err is JSONObject) {
                err.optString("message").ifBlank { err.toString() }.take(300)
            } else {
                obj.optString("detail", text).ifBlank { text }.take(300)
            }
        } catch (_: Exception) {
            text.take(300)
        }
    }

    private fun get(url: String, headers: Map<String, String>): JSONObject {
        val b = Request.Builder().url(url).get()
        headers.forEach { (k, v) -> b.header(k, v) }
        client.newCall(b.build()).execute().use { resp ->
            val text = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) throw RuntimeException("A IA recusou (HTTP ${resp.code}): ${errMsg(text)}")
            return JSONObject(text)
        }
    }

    private fun post(url: String, headers: Map<String, String>, body: JSONObject): JSONObject {
        val b = Request.Builder().url(url).post(body.toString().toRequestBody(JSON))
        headers.forEach { (k, v) -> b.header(k, v) }
        client.newCall(b.build()).execute().use { resp ->
            val text = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) throw RuntimeException("A IA recusou (HTTP ${resp.code}): ${errMsg(text)}")
            return JSONObject(text)
        }
    }

    /** Catálogo ao vivo de modelos da conta. */
    fun listModels(provider: String, key: String): List<String> {
        val data = when (provider) {
            "google" -> get(
                "$GOOGLE_BASE/models?pageSize=1000",
                mapOf("x-goog-api-key" to key)
            ).optJSONArray("models")?.let { arr ->
                (0 until arr.length()).mapNotNull { arr.optJSONObject(it)?.optString("name") }
            } ?: emptyList()
            "anthropic" -> get(
                "$ANTHROPIC_BASE/models",
                mapOf("x-api-key" to key, "anthropic-version" to "2023-06-01")
            ).optJSONArray("data")?.let { arr ->
                (0 until arr.length()).mapNotNull { arr.optJSONObject(it)?.optString("id") }
            } ?: emptyList()
            else -> get(
                "$OPENAI_BASE/models",
                mapOf("Authorization" to "Bearer $key")
            ).optJSONArray("data")?.let { arr ->
                (0 until arr.length()).mapNotNull { arr.optJSONObject(it)?.optString("id") }
            } ?: emptyList()
        }
        return data.map(::normalize).filter { it.isNotBlank() }.distinct()
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
        val prio = when (provider) {
            "google" -> GOOGLE_CHAT
            "anthropic" -> ANTHROPIC_CHAT
            else -> OPENAI_CHAT
        }
        val norm = models.map(::normalize)
        prio.firstOrNull { it in norm }?.let { return it }
        if (norm.isNotEmpty()) return norm[0]
        return when (provider) {
            "google" -> "gemini-3.1-pro-preview"
            "anthropic" -> "claude-sonnet-4-6"
            else -> throw RuntimeException("Sua conta não listou nenhum modelo de chat.")
        }
    }

    data class ChatOut(val provider: String, val model: String, val text: String)

    fun chat(provider: String, key: String, prompt: String): ChatOut {
        val model = pickChatModel(provider, listModels(provider, key))
        val text = when (provider) {
            "google" -> {
                val body = JSONObject()
                    .put("contents", JSONArray().put(JSONObject().put("role", "user").put("parts", JSONArray().put(JSONObject().put("text", prompt)))))
                    .put("generationConfig", JSONObject().put("temperature", 0.7))
                val res = post("$GOOGLE_BASE/models/$model:generateContent", mapOf("x-goog-api-key" to key), body)
                val parts = res.optJSONArray("candidates")
                    ?.optJSONObject(0)?.optJSONObject("content")?.optJSONArray("parts")
                val out = StringBuilder()
                if (parts != null) for (i in 0 until parts.length()) {
                    out.append(parts.optJSONObject(i)?.optString("text") ?: "")
                }
                out.toString().trim()
            }
            "anthropic" -> {
                val body = JSONObject()
                    .put("model", model)
                    .put("max_tokens", 4096)
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
                val res = post(
                    "$ANTHROPIC_BASE/messages",
                    mapOf("x-api-key" to key, "anthropic-version" to "2023-06-01"), body
                )
                val blocks = res.optJSONArray("content")
                val out = StringBuilder()
                if (blocks != null) for (i in 0 until blocks.length()) {
                    out.append(blocks.optJSONObject(i)?.optString("text") ?: "")
                }
                out.toString().trim()
            }
            else -> {
                val body = JSONObject()
                    .put("model", model)
                    .put("temperature", 0.7)
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", prompt)))
                val res = post("$OPENAI_BASE/chat/completions", mapOf("Authorization" to "Bearer $key"), body)
                val msg = res.optJSONArray("choices")?.optJSONObject(0)?.optJSONObject("message")
                (msg?.optString("content") ?: "").trim()
            }
        }
        if (text.isBlank()) throw RuntimeException("A IA não devolveu texto. Tente de novo.")
        return ChatOut(provider, model, text)
    }

    /** Inicia geração Veo direto no Google. Retorna (modelo, operação). */
    fun startVideo(
        key: String,
        prompt: String,
        aspectRatio: String,
        resolution: String,
        durationSeconds: Int,
        generateAudio: Boolean,
        negativePrompt: String?
    ): Pair<String, String> {
        val model = pickVideoModel(listModels("google", key))
        val params = JSONObject()
            .put("aspectRatio", aspectRatio)
            .put("resolution", resolution)
            .put("durationSeconds", durationSeconds)
            .put("generateAudio", generateAudio)
            .put("sampleCount", 1)
        if (!negativePrompt.isNullOrBlank()) params.put("negativePrompt", negativePrompt)
        val body = JSONObject()
            .put("instances", JSONArray().put(JSONObject().put("prompt", prompt)))
            .put("parameters", params)
        val res = post("$GOOGLE_BASE/models/$model:predictLongRunning", mapOf("x-goog-api-key" to key), body)
        var name = res.optString("name")
        if (name.isBlank()) name = res.optJSONObject("operation")?.optString("name") ?: ""
        if (name.isBlank()) throw RuntimeException("O Veo não devolveu a operação de vídeo.")
        return model to name
    }

    data class PollOut(val done: Boolean, val ref: JSONObject?)

    fun pollVideo(key: String, operation: String): PollOut {
        val url = if (operation.startsWith("http")) operation else "$GOOGLE_BASE/${operation.trimStart('/')}"
        val res = get(url, mapOf("x-goog-api-key" to key))
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

    fun downloadVideo(key: String, ref: JSONObject, dest: File) {
        val b64 = ref.optString("bytesBase64Encoded")
        if (b64.isNotBlank()) {
            dest.writeBytes(android.util.Base64.decode(b64, android.util.Base64.DEFAULT))
            return
        }
        val uri = ref.optString("uri").ifBlank { ref.optString("url") }
        if (uri.isBlank() || uri.startsWith("gs://")) throw RuntimeException(
            "O Veo devolveu um link que o app não consegue baixar direto."
        )
        val req = Request.Builder().url(uri).header("x-goog-api-key", key).build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) throw RuntimeException("Falha ao baixar o vídeo (HTTP ${resp.code}).")
            val body = resp.body ?: throw RuntimeException("Download vazio.")
            dest.outputStream().use { out -> body.byteStream().copyTo(out) }
        }
    }
}
