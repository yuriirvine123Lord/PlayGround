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

/** Netzack Videos V2: um chat só, um prompt só. Só a chave API — o app
 *  identifica sozinho o provedor (Google/OpenAI/Anthropic/compatível) e o modelo. */
class MainActivity : AppCompatActivity() {

    private lateinit var etServer: EditText
    private lateinit var tvHealth: TextView
    private lateinit var etKey: EditText
    private lateinit var etBase: EditText
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

        etServer = findViewById(R.id.etServer)
        tvHealth = findViewById(R.id.tvHealth)
        etKey = findViewById(R.id.etKey)
        etBase = findViewById(R.id.etBase)
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

        val prefs = getSharedPreferences("netzack", Context.MODE_PRIVATE)
        etServer.setText(prefs.getString("server", "http://10.0.2.2:8000"))

        findViewById<Button>(R.id.btnHealth).setOnClickListener { doHealth() }
        findViewById<Button>(R.id.btnDiscover).setOnClickListener { doDiscover() }
        findViewById<Button>(R.id.btnChat).setOnClickListener { doChat() }
        findViewById<Button>(R.id.btnCopy).setOnClickListener { copyChat() }
        findViewById<Button>(R.id.btnVideo).setOnClickListener { doVideo() }
        findViewById<Button>(R.id.btnPlay).setOnClickListener { playLast() }
    }

    private fun api(): NetzackApi {
        val server = etServer.text.toString().ifBlank { "http://10.0.2.2:8000" }
        getSharedPreferences("netzack", Context.MODE_PRIVATE).edit().putString("server", server).apply()
        return NetzackApi(server)
    }

    private fun baseOrNull(): String? = etBase.text.toString().ifBlank { null }

    private fun toast(msg: String) = runOnUiThread {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun doHealth() {
        tvHealth.text = "Testando…"
        thread {
            try {
                val raw = api().health()
                runOnUiThread { tvHealth.text = "Servidor OK: $raw" }
            } catch (e: Exception) {
                runOnUiThread {
                    tvHealth.text = "Não alcancei o servidor: ${e.message}\n" +
                        "No emulador use http://10.0.2.2:8000. No celular físico use http://SEU_IP:8000 com o backend rodando."
                }
            }
        }
    }

    private fun doDiscover() {
        val key = etKey.text.toString()
        if (key.isBlank()) {
            tvDiscover.text = "Cole sua chave API primeiro — só ela basta."
            return
        }
        tvDiscover.text = "Identificando IA e modelo…"
        thread {
            try {
                // provider sempre "auto" e model sempre null: detecção 100% automática
                val res = api().discover(key, "auto", baseOrNull())
                runOnUiThread {
                    tvDetected.text = "IA detectada: ${res.provider} • modelo: ${res.selectedModel} (chave ${ProviderDetector.redact(key)})"
                    tvDiscover.text = "Modelos: ${res.models.take(20).joinToString(", ")}\n\n${res.raw.take(2000)}"
                }
            } catch (e: Exception) {
                runOnUiThread { tvDiscover.text = "Erro: ${e.message}" }
            }
        }
    }

    private fun doChat() {
        val msg = etPrompt.text.toString()
        if (msg.isBlank()) { toast("Digite o prompt"); return }
        if (etKey.text.toString().isBlank()) { toast("Cole sua chave API primeiro"); return }
        tvChat.text = "Gerando resposta…"
        thread {
            try {
                val res = api().chat(etKey.text.toString(), "auto", baseOrNull(), msg)
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
        val basePrompt = etPrompt.text.toString()
        if (basePrompt.isBlank()) { toast("Digite o prompt"); return }
        if (etKey.text.toString().isBlank()) { toast("Cole sua chave API primeiro"); return }
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
                val job = a.createVideo(key, "auto", baseOrNull(), fullPrompt, null, ratio, resolution, duration, cbAudio.isChecked, effect.negativePrompt)
                runOnUiThread { tvVideo.text = "Job ${job.jobId}\nstatus=${job.status} modelo=${job.model}\nGerando (isso leva minutos no Veo)…" }
                var status = job
                var tries = 0
                while ((status.status == "queued" || status.status == "generating") && tries < 180) {
                    Thread.sleep(5000)
                    tries++
                    status = a.pollJob(job.jobId)
                    val s = status
                    runOnUiThread { tvVideo.text = "Job ${s.jobId}\nstatus=${s.status}\nmodelo=${s.model}" }
                }
                if (status.status == "completed") {
                    val dest = File(cacheDir, "${job.jobId}.mp4")
                    a.downloadToFile(job.jobId, dest)
                    lastVideoFile = dest
                    runOnUiThread {
                        tvVideo.text = "Pronto! Toque em Reproduzir."
                        videoView.setVideoPath(dest.absolutePath)
                        videoView.start()
                    }
                } else {
                    runOnUiThread { tvVideo.text = "Não gerou. Motivo: ${status.error}\nSe for acesso ao Veo, use uma chave Google com Veo liberado." }
                }
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
