package com.netzack.videos

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class ChatResult(val provider: String, val model: String, val text: String)
data class DiscoverResult(val provider: String, val selectedModel: String?, val models: List<String>, val raw: String)
data class VideoJob(val jobId: String, val status: String, val model: String?, val downloadUrl: String?, val error: String?, val raw: String)

/** Cliente HTTP mínimo para o backend Netzack Videos (FastAPI em server/). */
class NetzackApi(serverBase: String) {
    private val base = serverBase.trim().trimEnd('/')
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()
    private val json = "application/json; charset=utf-8".toMediaType()

    private fun fail(prefix: String, code: Int, text: String): Nothing {
        val detail = try {
            JSONObject(text).optString("detail", text).ifBlank { text }
        } catch (_: Exception) {
            text
        }
        throw RuntimeException("$prefix (HTTP $code): ${detail.take(500)}")
    }

    private fun post(path: String, body: JSONObject): JSONObject {
        val req = Request.Builder()
            .url("$base$path")
            .post(body.toString().toRequestBody(json))
            .build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) fail("O servidor recusou", resp.code, text)
            return JSONObject(text)
        }
    }

    private fun get(path: String): JSONObject {
        val req = Request.Builder().url("$base$path").get().build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) fail("Falha ao consultar", resp.code, text)
            return JSONObject(text)
        }
    }

    fun health(): String {
        val req = Request.Builder().url("$base/health").get().build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: "{}"
            if (!resp.isSuccessful) fail("Servidor respondeu com erro", resp.code, text)
            return text
        }
    }

    fun discover(apiKey: String, provider: String, baseUrl: String?): DiscoverResult {
        val body = JSONObject()
            .put("provider", provider.ifBlank { "auto" })
        if (apiKey.isNotBlank()) body.put("api_key", apiKey)
        if (!baseUrl.isNullOrBlank()) body.put("base_url", baseUrl)
        val res = post("/v1/discover", body)
        val models = mutableListOf<String>()
        val arr = res.optJSONArray("models")
        if (arr != null) for (i in 0 until arr.length()) models.add(arr.optString(i))
        return DiscoverResult(
            res.optString("provider"),
            res.optString("selected_model").ifBlank { null },
            models,
            res.toString(2)
        )
    }

    fun chat(apiKey: String, provider: String, baseUrl: String?, message: String, model: String? = null): ChatResult {
        val body = JSONObject()
            .put("provider", provider.ifBlank { "auto" })
            .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", message)))
            .put("temperature", 0.7)
        if (apiKey.isNotBlank()) body.put("api_key", apiKey)
        if (!baseUrl.isNullOrBlank()) body.put("base_url", baseUrl)
        if (!model.isNullOrBlank()) body.put("model", model)
        val res = post("/v1/chat", body)
        return ChatResult(res.optString("provider"), res.optString("model"), res.optString("text"))
    }

    fun createVideo(
        apiKey: String, provider: String, baseUrl: String?,
        prompt: String, model: String?,
        aspectRatio: String, resolution: String,
        durationSeconds: Int, generateAudio: Boolean,
        negativePrompt: String?
    ): VideoJob {
        val body = JSONObject()
            .put("provider", provider.ifBlank { "auto" })
            .put("prompt", prompt)
            .put("aspect_ratio", aspectRatio)
            .put("resolution", resolution)
            .put("duration_seconds", durationSeconds)
            .put("generate_audio", generateAudio)
        if (apiKey.isNotBlank()) body.put("api_key", apiKey)
        if (!baseUrl.isNullOrBlank()) body.put("base_url", baseUrl)
        if (!model.isNullOrBlank()) body.put("model", model)
        if (!negativePrompt.isNullOrBlank()) body.put("negative_prompt", negativePrompt)
        val res = post("/v1/videos", body)
        return VideoJob(
            res.optString("job_id"), res.optString("status"),
            res.optString("model").ifBlank { null },
            res.optString("download_url").ifBlank { null },
            res.optString("error").ifBlank { null }, res.toString(2)
        )
    }

    fun pollJob(jobId: String): VideoJob {
        val res = get("/v1/videos/$jobId")
        return VideoJob(
            res.optString("job_id"), res.optString("status"),
            res.optString("model").ifBlank { null },
            res.optString("download_url").ifBlank { null },
            res.optString("error").ifBlank { null }, res.toString(2)
        )
    }

    fun downloadToFile(jobId: String, dest: File) {
        val req = Request.Builder().url("$base/v1/videos/$jobId/download").get().build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) {
                val text = try {
                    resp.body?.string() ?: ""
                } catch (_: Exception) {
                    ""
                }
                fail("Falha ao baixar o vídeo", resp.code, text.ifBlank { "{}" })
            }
            val body = resp.body ?: throw RuntimeException("Resposta vazia no download")
            dest.outputStream().use { out -> body.byteStream().copyTo(out) }
        }
    }
}
