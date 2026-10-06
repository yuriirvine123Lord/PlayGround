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

class MainActivity : AppCompatActivity() {

    private lateinit var etServer: EditText
    private lateinit var etKey: EditText
    private lateinit var spProvider: Spinner
    private lateinit var tvDetected: TextView
    private lateinit var etBase: EditText
    private lateinit var tvDiscover: TextView
    private lateinit var etChat: EditText
    private lateinit var tvChat: TextView
    private lateinit var etVideo: EditText
    private lateinit var spEffect: Spinner
    private lateinit var spRatio: Spinner
    private lateinit var spResolution: Spinner
    private lateinit var spDuration: Spinner
    private lateinit var cbAudio: CheckBox
    private lateinit var tvVideo: TextView
    private lateinit var videoView: VideoView

    private var lastVideoFile: File? = null
    private val providerValues = listOf("auto", "google", "openai", "anthropic", "openai_compatible")
    private val providerLabels = listOf("Auto detectar", "Google / Gemini / Veo", "OpenAI", "Anthropic", "OpenAI compatível")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etServer = findViewById(R.id.etServer)
        etKey = findViewById(R.id.etKey)
        spProvider = findViewById(R.id.spProvider)
        tvDetected = findViewById(R.id.tvDetected)
        etBase = findViewById(R.id.etBase)
        tvDiscover = findViewById(R.id.tvDiscover)
        etChat = findViewById(R.id.etChat)
        tvChat = findViewById(R.id.tvChat)
        etVideo = findViewById(R.id.etVideo)
        spEffect = findViewById(R.id.spEffect)
        spRatio = findViewById(R.id.spRatio)
        spResolution = findViewById(R.id.spResolution)
        spDuration = findViewById(R.id.spDuration)
        cbAudio = findViewById(R.id.cbAudio)
        tvVideo = findViewById(R.id.tvVideo)
        videoView = findViewById(R.id.videoView)

        spProvider.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, providerLabels)
        spEffect.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, Effects.ALL.map { it.name })
        spRatio.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("16:9", "9:16"))
        spResolution.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("720p", "1080p", "4k"))
        spDuration.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, listOf("4", "6", "8"))
        spDuration.setSelection(2)

        // Restaura servidor salvo (nunca a chave por segurança extra — usuário digita a cada sessão)
        val prefs = getSharedPreferences("netzack", Context.MODE_PRIVATE)
        etServer.setText(prefs.getString("server", "http://10.0.2.2:8000"))

        findViewById<Button>(R.id.btnDiscover).setOnClickListener { doDiscover() }
        findViewById<Button>(R.id.btnChat).setOnClickListener { doChat() }
        findViewById<Button>(R.id.btnCopy).setOnClickListener { copyChat() }
        findViewById<Button>(R.id.btnVideo).setOnClickListener { doVideo() }
        findViewById<Button>(R.id.btnPlay).setOnClickListener { playLast() }
    }

    private fun provider(): String = providerValues[spProvider.selectedItemPosition]

    private fun api(): NetzackApi {
        val server = etServer.text.toString().ifBlank { "http://10.0.2.2:8000" }
        getSharedPreferences("netzack", Context.MODE_PRIVATE).edit().putString("server", server).apply()
        return NetzackApi(server)
    }

    private fun toast(msg: String) = runOnUiThread {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun doDiscover() {
        val key = etKey.text.toString()
        val base = etBase.text.toString().ifBlank { null }
        tvDiscover.text = "Consultando catálogo…"
        thread {
            try {
                val res = api().discover(key, provider(), base)
                runOnUiThread {
                    tvDetected.text = "Provedor detectado: ${res.provider} (escolha: ${providerLabels[spProvider.selectedItemPosition]}, chave ${ProviderDetector.redact(key.ifBlank { "********" })})"
                    tvDiscover.text = "Modelo: ${res.selectedModel}\nModelos: ${res.models.take(20).joinToString(", ")}\n\n${res.raw.take(2000)}"
                }
            } catch (e: Exception) {
                runOnUiThread { tvDiscover.text = "Erro: ${e.message}" }
            }
        }
    }

    private fun doChat() {
        val msg = etChat.text.toString()
        if (msg.isBlank()) { toast("Digite a mensagem do roteiro"); return }
        tvChat.text = "Gerando resposta…"
        thread {
            try {
                val res = api().chat(etKey.text.toString(), provider(), etBase.text.toString().ifBlank { null }, msg)
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
        val basePrompt = etVideo.text.toString()
        if (basePrompt.isBlank()) { toast("Descreva a cena do vídeo"); return }
        val effect = Effects.ALL[spEffect.selectedItemPosition]
        val fullPrompt = (basePrompt + effect.promptSuffix).trim()
        val ratio = if (spRatio.selectedItemPosition == 0) "16:9" else "9:16"
        val resolution = listOf("720p", "1080p", "4k")[spResolution.selectedItemPosition]
        val duration = listOf(4, 6, 8)[spDuration.selectedItemPosition]
        tvVideo.text = "Enfileirando… (efeito: ${effect.name})"
        thread {
            try {
                val a = api()
                val key = etKey.text.toString()
                val base = etBase.text.toString().ifBlank { null }
                val job = a.createVideo(key, provider(), base, fullPrompt, null, ratio, resolution, duration, cbAudio.isChecked, effect.negativePrompt)
                runOnUiThread { tvVideo.text = "Job ${job.jobId} status=${job.status} modelo=${job.model}\nAguardando Veo (polling)…" }
                var status = job
                var tries = 0
                while ((status.status == "queued" || status.status == "generating") && tries < 180) {
                    Thread.sleep(5000)
                    tries++
                    status = a.pollJob(job.jobId)
                    val s = status
                    runOnUiThread { tvVideo.text = "Job ${s.jobId}\nstatus=${s.status}\nmodelo=${s.model}\n${s.raw.take(1000)}" }
                }
                if (status.status == "completed") {
                    val dest = File(cacheDir, "${job.jobId}.mp4")
                    a.downloadToFile(job.jobId, dest)
                    lastVideoFile = dest
                    runOnUiThread {
                        tvVideo.text = "Pronto! Salvo em cache: ${dest.absolutePath}\nToque em Reproduzir."
                        videoView.setVideoPath(dest.absolutePath)
                        videoView.start()
                    }
                } else {
                    runOnUiThread { tvVideo.text = "Falhou: ${status.error}\n${status.raw.take(1000)}" }
                }
            } catch (e: Exception) {
                runOnUiThread { tvVideo.text = "Erro: ${e.message}" }
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
