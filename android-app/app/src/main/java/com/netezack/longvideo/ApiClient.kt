package com.netezack.longvideo

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class ChatMsg(val role: String, val content: String)
data class EffectInfo(val id: String, val label: String, val desc: String)
data class VideoJob(
    val jobId: String,
    val status: String,
    val provider: String,
    val progress: Int,
    val stage: String?,
    val effects: List<String>,
    val fallbackUsed: Boolean,
    val previewUrl: String?,
    val downloadUrl: String?,
    val error: String?,
    val frames: Int?,
    val totalFrames: Int?
)

class ApiClient(baseUrlRaw: String, private val apiKey: String) {
    val baseUrl = baseUrlRaw.trim().trimEnd('/')
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private fun creds(obj: JSONObject): JSONObject {
        if (apiKey.isNotBlank()) obj.put("api_key", apiKey)
        obj.put("provider", "auto")
        return obj
    }

    suspend fun health(): Int = withContext(Dispatchers.IO) {
        val req = Request.Builder().url("$baseUrl/health").get().build()
        http.newCall(req).execute().use { it.code }
    }

    suspend fun listEffects(): List<EffectInfo> = withContext(Dispatchers.IO) {
        val req = Request.Builder().url("$baseUrl/v1/effects").get().build()
        http.newCall(req).execute().use { resp ->
            if (resp.code != 200) throw Exception("effects HTTP ${resp.code}")
            val body = resp.body?.string() ?: throw Exception("resposta vazia")
            val arr = JSONObject(body).optJSONArray("effects") ?: JSONArray()
            List(arr.length()) { i ->
                val o = arr.getJSONObject(i)
                EffectInfo(o.optString("id"), o.optString("label"), o.optString("desc"))
            }
        }
    }

    suspend fun chat(messages: List<ChatMsg>): String = withContext(Dispatchers.IO) {
        val body = creds(JSONObject())
        val arr = JSONArray()
        messages.forEach { arr.put(JSONObject().put("role", it.role).put("content", it.content)) }
        body.put("messages", arr)
        body.put("temperature", 0.7)
        val req = Request.Builder().url("$baseUrl/v1/chat")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        http.newCall(req).execute().use { resp ->
            val txt = resp.body?.string() ?: ""
            if (resp.code != 200) throw Exception(parseDetail(txt, resp.code))
            JSONObject(txt).optString("text", "")
        }
    }

    suspend fun createVideo(
        prompt: String,
        aspect: String,
        resolution: String,
        durationSeconds: Int,
        effects: List<String>
    ): VideoJob = withContext(Dispatchers.IO) {
        val body = creds(JSONObject())
        body.put("prompt", prompt)
        body.put("aspect_ratio", aspect)
        body.put("resolution", resolution)
        body.put("duration_seconds", durationSeconds)
        body.put("effects", JSONArray(effects))
        body.put("use_fallback", true)
        val req = Request.Builder().url("$baseUrl/v1/videos")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        http.newCall(req).execute().use { resp ->
            val txt = resp.body?.string() ?: ""
            if (resp.code != 200 && resp.code != 202) throw Exception(parseDetail(txt, resp.code))
            parseJob(JSONObject(txt))
        }
    }

    suspend fun getJob(jobId: String): VideoJob = withContext(Dispatchers.IO) {
        val req = Request.Builder().url("$baseUrl/v1/videos/$jobId").get().build()
        http.newCall(req).execute().use { resp ->
            val txt = resp.body?.string() ?: ""
            if (resp.code != 200) throw Exception(parseDetail(txt, resp.code))
            parseJob(JSONObject(txt))
        }
    }

    fun previewUrl(job: VideoJob, cacheBuster: Long): String? {
        val p = job.previewUrl ?: return null
        val abs = if (p.startsWith("http")) p else baseUrl + p
        return "$abs?t=$cacheBuster"
    }

    fun downloadUrl(job: VideoJob): String? {
        val d = job.downloadUrl ?: return null
        return if (d.startsWith("http")) d else baseUrl + d
    }

    suspend fun downloadTo(job: VideoJob, dest: java.io.File) = withContext(Dispatchers.IO) {
        val url = downloadUrl(job) ?: throw Exception("sem download_url")
        val req = Request.Builder().url(url).get().build()
        http.newCall(req).execute().use { resp ->
            if (resp.code != 200) throw Exception("download HTTP ${resp.code}")
            dest.outputStream().use { out -> resp.body!!.byteStream().copyTo(out) }
        }
    }

    private fun parseJob(o: JSONObject): VideoJob {
        val eff = mutableListOf<String>()
        o.optJSONArray("effects")?.let { a ->
            for (i in 0 until a.length()) eff.add(a.optString(i))
        }
        return VideoJob(
            jobId = o.optString("job_id"),
            status = o.optString("status"),
            provider = o.optString("provider"),
            progress = o.optInt("progress", 0),
            stage = o.optString("stage").ifBlank { null },
            effects = eff,
            fallbackUsed = o.optBoolean("fallback_used", false),
            previewUrl = o.optString("preview_url").ifBlank { null },
            downloadUrl = o.optString("download_url").ifBlank { null },
            error = o.optString("error").ifBlank { null },
            frames = if (o.has("frames") && !o.isNull("frames")) o.optInt("frames") else null,
            totalFrames = if (o.has("total_frames") && !o.isNull("total_frames")) o.optInt("total_frames") else null
        )
    }

    private fun parseDetail(txt: String, code: Int): String {
        return try {
            val d = JSONObject(txt).optString("detail", txt)
            "HTTP $code: $d"
        } catch (_: Exception) {
            "HTTP $code: ${txt.take(300)}"
        }
    }
}
