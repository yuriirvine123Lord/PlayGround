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
 *  Sem servidor, sem base URL — endpoints e modelos já vêm embarcados e o app
 *  identifica sozinho o provedor (Google/OpenAI/Anthropic) e o modelo. */
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
        spDuration.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("4", "6", "8"))
        spDuration.setSelection(2)

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
        if (k.isBlank()) toast("Cole sua chave API primeiro — só ela basta")
        return k.ifBlank { null }
    }

    private fun doDiscover() {
        val key = keyOrAsk() ?: return
        tvDiscover.text = "Identificando IA e modelo…"
        thread {
            try {
                val provider = DirectAI.detect(key)
                val models = DirectAI.listModels(provider, key)
                val chatModel = DirectAI.pickChatModel(provider, models)
                val videoModel = try {
                    DirectAI.pickVideoModel(models)
                } catch (e: Exception) {
                    null
                }
                runOnUiThread {
                    tvDetected.text = "IA: $provider • chat: $chatModel • vídeo: ${videoModel ?: "sem Veo liberado"} (chave ${DirectAI.redact(key)})"
                    tvDiscover.text = "Modelos da sua conta: ${models.take(25).joinToString(", ")}"
                }
            } catch (e: Exception) {
                runOnUiThread { tvDiscover.text = "Erro: ${e.message}" }
            }
        }
    }

    private fun doChat() {
        val key = keyOrAsk() ?: return
        val msg = etPrompt.text.toString().trim()
        if (msg.isBlank()) { toast("Digite o prompt"); return }
        tvChat.text = "Gerando resposta…"
        thread {
            try {
                val res = DirectAI.chat(DirectAI.detect(key), key, msg)
                runOnUiThread { tvChat.text = "[${res.provider}/${res.model}]\n\n${res.text}" }
            } catch (e: Exception) {
                runOnUiThread { tvChat.text = "Erro: ${e.message}" }
            }
        }
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
        val fullPrompt = (basePrompt + effect.promptSuffix).trim()
        val ratio = if (spRatio.selectedItemPosition == 0) "16:9" else "9:16"
        val resolution = listOf("720p", "1080p", "4k")[spResolution.selectedItemPosition]
        val duration = listOf(4, 6, 8)[spDuration.selectedItemPosition]
        tvVideo.text = "Iniciando… (efeito: ${effect.name})"
        thread {
            try {
                val provider = DirectAI.detect(key)
                if (provider != "google") {
                    runOnUiThread { tvVideo.text = "Vídeo precisa de chave Google (AIza…) com Veo. Sua chave é de: $provider (serve para Conversar)." }
                    return@thread
                }
                val (model, op) = DirectAI.startVideo(key, fullPrompt, ratio, resolution, duration, cbAudio.isChecked, effect.negativePrompt)
                runOnUiThread { tvVideo.text = "Modelo $model gerando… (o Veo leva minutos, aguarde)" }
                var tries = 0
                while (tries < 90) {
                    Thread.sleep(10000)
                    tries++
                    val poll = DirectAI.pollVideo(key, op)
                    if (poll.done && poll.ref != null) {
                        val dest = File(cacheDir, "netzack-${System.currentTimeMillis()}.mp4")
                        DirectAI.downloadVideo(key, poll.ref, dest)
                        lastVideoFile = dest
                        runOnUiThread {
                            tvVideo.text = "Pronto! Toque em Reproduzir."
                            videoView.setVideoPath(dest.absolutePath)
                            videoView.start()
                        }
                        return@thread
                    }
                    val t = tries
                    runOnUiThread { tvVideo.text = "Modelo $model gerando… (${t * 10}s, aguarde)" }
                }
                runOnUiThread { tvVideo.text = "Demorou demais — tente de novo com um prompt mais curto." }
            } catch (e: Exception) {
                runOnUiThread { tvVideo.text = "Não gerou. Motivo: ${e.message}" }
            }
        }
    }

    private fun playLast() {
        val f = lastVideoFile
        if (f == null || !f.exists()) { toast("Gere um vídeo primeiro"); return }
        videoView.setVideoPath(f.absolutePath)
        videoView.start()
    }
}
