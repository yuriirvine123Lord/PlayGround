package com.netzack.videos

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import android.widget.VideoView
import androidx.appcompat.app.AppCompatActivity
import java.io.File
import kotlin.concurrent.thread

/** Netzack Videos V2: um chat só, um prompt só, SÓ a chave API.
 *  Cole qualquer chave de qualquer provedor do mercado — o app identifica
 *  sozinho (URLs embarcadas, nunca exibidas) e gera vídeo até 10 minutos. */
class MainActivity : AppCompatActivity() {

    private lateinit var etKey: EditText
    private lateinit var tvDetected: TextView
    private lateinit var tvDiscover: TextView
    private lateinit var etPrompt: EditText
    private lateinit var spEffect: Spinner
    private lateinit var spRatio: Spinner
    private lateinit var spResolution: Spinner
    private lateinit var spDuration: Spinner
    private lateinit var cbAudio: CheckBox
    private lateinit var tvChat: TextView
    private lateinit var tvVideo: TextView
    private lateinit var videoView: VideoView

    private var lastVideoFile: File? = null
    private var playQueue: List<File> = emptyList()
    private var playIndex = 0

    private var detectedEp: DirectAI.Endpoint? = null

    private val durationLabels = listOf("4 s", "6 s", "8 s", "15 s", "30 s", "1 min", "2 min", "5 min", "10 min")
    private val durationValues = listOf(4, 6, 8, 15, 30, 60, 120, 300, 600)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etKey = findViewById(R.id.etKey)
        tvDetected = findViewById(R.id.tvDetected)
        tvDiscover = findViewById(R.id.tvDiscover)
        etPrompt = findViewById(R.id.etPrompt)
        spEffect = findViewById(R.id.spEffect)
        spRatio = findViewById(R.id.spRatio)
        spResolution = findViewById(R.id.spResolution)
        spDuration = findViewById(R.id.spDuration)
        cbAudio = findViewById(R.id.cbAudio)
        tvChat = findViewById(R.id.tvChat)
        tvVideo = findViewById(R.id.tvVideo)
        videoView = findViewById(R.id.videoView)

        spEffect.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, Effects.ALL.map { it.name })
        spRatio.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("16:9", "9:16"))
        spResolution.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("720p", "1080p", "4k"))
        spDuration.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, durationLabels)
        spDuration.setSelection(2) // 8 s por padrão

        videoView.setOnCompletionListener {
            playIndex++
            if (playIndex < playQueue.size) {
                videoView.setVideoPath(playQueue[playIndex].absolutePath)
                videoView.start()
            }
        }

        findViewById<Button>(R.id.btnDiscover).setOnClickListener { doDiscover() }
        findViewById<Button>(R.id.btnChat).setOnClickListener { doChat() }
        findViewById<Button>(R.id.btnCopy).setOnClickListener { copyChat() }
        findViewById<Button>(R.id.btnVideo).setOnClickListener { doVideo() }
        findViewById<Button>(R.id.btnPlay).setOnClickListener { playLast() }
    }

    private fun toast(msg: String) = runOnUiThread {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun keyOrAsk(): String? {
        val k = etKey.text.toString().trim()
        if (k.isBlank()) toast("Cole sua chave API primeiro — qualquer uma, o app identifica sozinho")
        return k.ifBlank { null }
    }

    /** Identifica qualquer chave testando os endpoints embarcados (ocultos). */
    private fun identifyAsync(onOk: (DirectAI.Endpoint) -> Unit, onFail: (String) -> Unit) {
        val key = keyOrAsk() ?: return
        detectedEp?.let { onOk(it); return }
        tvDiscover.text = "Identificando a IA…"
        thread {
            try {
                val ep = DirectAI.identify(key) { i, n ->
                    runOnUiThread { tvDiscover.text = "Identificando a IA… ($i/$n provedores testados)" }
                }
                detectedEp = ep
                runOnUiThread { tvDiscover.text = "Pronto." }
                onOk(ep)
            } catch (e: Exception) {
                runOnUiThread { onFail(e.message ?: "Erro desconhecido") }
            }
        }
    }

    private fun doDiscover() {
        val key = keyOrAsk() ?: return
        tvDetected.text = "IA detectada: —"
        identifyAsync(onOk = { ep ->
            thread {
                try {
                    val models = DirectAI.listModels(ep, key)
                    val chatModel = DirectAI.pickChatModel(ep.id, models)
                    val videoModel = try {
                        DirectAI.pickVideoModel(models)
                    } catch (_: Exception) {
                        null
                    }
                    runOnUiThread {
                        tvDetected.text = "IA: ${ep.name} • chat: $chatModel • vídeo: ${videoModel ?: "chat-only"} (chave ${DirectAI.redact(key)})"
                        tvDiscover.text = "Modelos da sua conta: ${models.take(25).joinToString(", ")}"
                    }
                } catch (e: Exception) {
                    runOnUiThread { tvDiscover.text = "Erro: ${e.message}" }
                }
            }
        }, onFail = { msg ->
            tvDiscover.text = "Erro: $msg"
            tvDetected.text = "IA detectada: —"
        })
    }

    private fun doChat() {
        val key = keyOrAsk() ?: return
        val msg = etPrompt.text.toString().trim()
        if (msg.isBlank()) { toast("Digite o prompt"); return }
        tvChat.text = "Gerando resposta…"
        identifyAsync(onOk = { ep ->
            thread {
                try {
                    val res = DirectAI.chat(ep, key, msg)
                    runOnUiThread { tvChat.text = "[${res.provider}/${res.model}]\n\n${res.text}" }
                } catch (e: Exception) {
                    runOnUiThread { tvChat.text = "Erro: ${e.message}" }
                }
            }
        }, onFail = { msg ->
            tvChat.text = "Erro: $msg"
        })
    }

    private fun copyChat() {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("netzack", tvChat.text.toString()))
        toast("Resposta copiada")
    }

    private fun doVideo() {
        val key = keyOrAsk() ?: return
        val basePrompt = etPrompt.text.toString().trim()
        if (basePrompt.isBlank()) { toast("Digite o prompt"); return }
        val effect = Effects.ALL[spEffect.selectedItemPosition]
        val ratio = if (spRatio.selectedItemPosition == 0) "16:9" else "9:16"
        val resolution = listOf("720p", "1080p", "4k")[spResolution.selectedItemPosition]
        val total = durationValues[spDuration.selectedItemPosition]
        val audio = cbAudio.isChecked

        identifyAsync(onOk = { ep ->
            thread {
                try {
                    runGeneration(ep, key, basePrompt, effect, ratio, resolution, total, audio)
                } catch (e: Exception) {
                    runOnUiThread { tvVideo.text = "Não gerou. Motivo: ${e.message}" }
                }
            }
        }, onFail = { msg ->
            tvVideo.text = "Não gerou. Motivo: $msg"
        })
    }

    private fun runGeneration(
        ep: DirectAI.Endpoint,
        key: String,
        basePrompt: String,
        effect: EffectPreset,
        ratio: String,
        resolution: String,
        total: Int,
        audio: Boolean
    ) {
        val chunks: List<Int>
        val mode: String
        when {
            ep.id == "google" -> {
                chunks = DirectAI.splitDuration(total, DirectAI.VEO_CHUNKS)
                mode = "veo"
            }
            ep.id == "openai" -> {
                chunks = DirectAI.splitDuration(total, DirectAI.SORA_CHUNKS)
                mode = "sora"
            }
            else -> {
                runOnUiThread {
                    tvVideo.text = "Vídeo disponível com chave Google (AIza…, Veo) ou OpenAI (Sora). " +
                        "Sua IA (${ep.name}) está pronta para Conversar."
                }
                return
            }
        }

        val files = mutableListOf<File>()
        for ((i, secs) in chunks.withIndex()) {
            val clipPrompt = if (i == 0) {
                (basePrompt + effect.promptSuffix).trim()
            } else {
                (basePrompt + effect.promptSuffix + ", continuous seamless sequel of the same scene, same style and characters, next moment").trim()
            }
            runOnUiThread {
                tvVideo.text = "Gerando pedaço ${i + 1}/${chunks.size} (${secs}s)… " +
                    "até 10 min são vários pedaços; aguarde."
            }
            val dest = File(cacheDir, "netzack-clip-${i}-${System.currentTimeMillis()}.mp4")
            when (mode) {
                "veo" -> genVeoClip(key, clipPrompt, ratio, resolution, secs, audio, effect, i, chunks.size, dest)
                else -> genSoraClip(key, clipPrompt, secs, resolution, ratio, i, chunks.size, dest)
            }
            files.add(dest)
        }

        val stitched = File(cacheDir, "netzack-full-${System.currentTimeMillis()}.mp4")
        val ok = VideoStitcher.concat(files, stitched)
        playQueue = files
        playIndex = 0
        if (ok) {
            lastVideoFile = stitched
            playQueue = listOf(stitched)
            runOnUiThread {
                tvVideo.text = "Pronto! ${chunks.size} pedaço(s) unidos em ${total}s (aprox.). Toque em Reproduzir."
                videoView.setVideoPath(stitched.absolutePath)
                videoView.start()
            }
        } else {
            lastVideoFile = files.firstOrNull()
            runOnUiThread {
                tvVideo.text = "Pronto! ${files.size} pedaço(s) de ${total}s. Toque em Reproduzir (toca em sequência)."
                if (files.isNotEmpty()) {
                    playIndex = 0
                    videoView.setVideoPath(files[0].absolutePath)
                    videoView.start()
                }
            }
        }
    }

    private fun genVeoClip(
        key: String, prompt: String, ratio: String, resolution: String,
        secs: Int, audio: Boolean, effect: EffectPreset, idx: Int, totalClips: Int, dest: File
    ) {
        val (model, op) = DirectAI.startVeo(key, prompt, ratio, resolution, secs, audio, effect.negativePrompt)
        var tries = 0
        while (tries < 120) {
            Thread.sleep(8000)
            tries++
            val poll = DirectAI.pollVeo(key, op)
            if (poll.done && poll.ref != null) {
                DirectAI.downloadVeo(key, poll.ref, dest)
                return
            }
            val t = tries * 8
            runOnUiThread { tvVideo.text = "Pedaço ${idx + 1}/$totalClips gerando… ($model, ${t}s aguardando)" }
        }
        throw RuntimeException("O Veo demorou demais no pedaço ${idx + 1}. Tente um tempo menor.")
    }

    private fun genSoraClip(
        key: String, prompt: String, secs: Int, resolution: String, ratio: String,
        idx: Int, totalClips: Int, dest: File
    ) {
        val size = DirectAI.soraSize(ratio, resolution)
        val id = DirectAI.startSora(key, prompt, secs, size)
        var tries = 0
        while (tries < 150) {
            Thread.sleep(5000)
            tries++
            val (done, err) = DirectAI.pollSora(key, id)
            if (err != null) throw RuntimeException(err)
            if (done) {
                DirectAI.downloadSora(key, id, dest)
                return
            }
            val t = tries * 5
            runOnUiThread { tvVideo.text = "Pedaço ${idx + 1}/$totalClips gerando… (Sora, ${t}s aguardando)" }
        }
        throw RuntimeException("O Sora demorou demais no pedaço ${idx + 1}.")
    }

    private fun playLast() {
        if (playQueue.isNotEmpty() && playQueue.all { it.exists() }) {
            playIndex = 0
            videoView.setVideoPath(playQueue[0].absolutePath)
            videoView.start()
            return
        }
        val f = lastVideoFile
        if (f == null || !f.exists()) { toast("Gere um vídeo primeiro"); return }
        videoView.setVideoPath(f.absolutePath)
        videoView.start()
    }
}
