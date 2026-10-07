package com.netezack.longvideo

import android.net.Uri
import android.os.Bundle
import android.widget.MediaController
import android.widget.VideoView
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import coil.compose.AsyncImage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File

private val Neon = Color(0xFF00F5D4)
private val Magenta = Color(0xFFFF2E88)
private val Bg = Color(0xFF04060B)

data class UiChat(val who: String, val text: String)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(background = Bg, surface = Bg)) {
                Surface(Modifier.fillMaxSize(), color = Bg) { App() }
            }
        }
    }
}

@Composable
fun App() {
    var baseUrl by remember { mutableStateOf("") }
    var apiKey by remember { mutableStateOf("") }
    var showKey by remember { mutableStateOf(false) }
    var healthMsg by remember { mutableStateOf("status: aguardando teste") }
    var healthOk by remember { mutableStateOf(false) }
    var tab by remember { mutableIntStateOf(1) }
    val scope = rememberCoroutineScope()

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Text("⚡ LONGVIDEOV2", color = Neon, fontSize = 18.sp, fontFamily = FontFamily.Monospace)
        Text("app nativo Kotlin · IA do projeto LongvideoV2 · digite a URL do seu servidor", color = Color.Gray, fontSize = 11.sp)
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = baseUrl, onValueChange = { baseUrl = it },
            label = { Text("URL do servidor LongvideoV2") }, modifier = Modifier.fillMaxWidth(), singleLine = true,
            placeholder = { Text("https://seu-servidor") }
        )
        OutlinedTextField(
            value = apiKey, onValueChange = { apiKey = it },
            label = { Text("API KEY (servidor identifica sozinho)") },
            modifier = Modifier.fillMaxWidth(), singleLine = true,
            visualTransformation = if (showKey) VisualTransformation.None else PasswordVisualTransformation()
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Button(onClick = {
                scope.launch {
                    healthMsg = "testando…"
                    healthOk = false
                    try {
                        val code = ApiClient(baseUrl, apiKey).health()
                        healthOk = code == 200
                        healthMsg = if (code == 200) "200 OK · servidor no ar" else "HTTP $code"
                    } catch (e: Exception) {
                        healthMsg = "erro: ${e.message?.take(160)}"
                    }
                }
            }) { Text("TESTAR (GET /health)") }
            OutlinedButton(onClick = { showKey = !showKey }) { Text(if (showKey) "ocultar" else "mostrar") }
        }
        Text(healthMsg, color = if (healthOk) Neon else Magenta, fontSize = 12.sp)
        Spacer(Modifier.height(4.dp))
        TabRow(selectedTabIndex = tab) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("// chat IA") })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("// gerar vídeo 2-3min") })
        }
        if (tab == 0) ChatScreen(baseUrl, apiKey) else VideoScreen(baseUrl, apiKey)
    }
}

@Composable
fun ChatScreen(baseUrl: String, apiKey: String) {
    val msgs = remember { mutableStateListOf(UiChat("ai", "NEON online. Fala o que você quer criar.")) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    LaunchedEffect(msgs.size) { if (msgs.isNotEmpty()) listState.animateScrollToItem(msgs.size - 1) }

    Column(Modifier.fillMaxWidth().padding(top = 8.dp)) {
        LazyColumn(state = listState, modifier = Modifier.weight(1f).fillMaxWidth()) {
            items(msgs) { m ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (m.who == "user") Color(0xFF0B1226) else Color(0xFF060A12)
                    )
                ) { Text(m.text, Modifier.padding(9.dp), fontSize = 12.5.sp) }
            }
        }
        OutlinedTextField(value = input, onValueChange = { input = it },
            label = { Text("sua ordem") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(enabled = !busy && input.isNotBlank(), onClick = {
                val q = input.trim()
                msgs.add(UiChat("user", q))
                input = ""
                busy = true
                scope.launch {
                    try {
                        val api = ApiClient(baseUrl, apiKey)
                        val out = api.chat(listOf(ChatMsg("user", q)))
                        msgs.add(UiChat("ai", out.take(2000)))
                    } catch (e: Exception) {
                        msgs.add(UiChat("ai", "erro: ${e.message?.take(400)}"))
                    } finally { busy = false }
                }
            }) { Text(if (busy) "…" else "ENVIAR") }
            if (busy) CircularProgressIndicator(Modifier.align(Alignment.CenterVertically))
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun VideoScreen(baseUrl: String, apiKey: String) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var prompt by remember { mutableStateOf("") }
    var aspect by remember { mutableStateOf("16:9") }
    var duration by remember { mutableIntStateOf(150) } // 2.5min padrão: 2-3min em <5min
    var selectedFx = remember { mutableStateListOf<String>() }
    var allFx by remember { mutableStateOf(listOf<EffectInfo>()) }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("job aparece aqui com progresso real") }
    var stage by remember { mutableStateOf("") }
    var progress by remember { mutableIntStateOf(0) }
    var previewTick by remember { mutableStateOf(0L) }
    var previewUrl by remember { mutableStateOf<String?>(null) }
    var videoFile by remember { mutableStateOf<File?>(null) }
    var lastRes by remember { mutableStateOf("720p") }

    // 720p fixo p/ 2-3min: backend rebaixa 1080p->720p acima de 120s p/ fechar em <5min
    val durations = listOf(8, 15, 30, 60, 120, 150, 180)
    LaunchedEffect(baseUrl) {
        try { allFx = ApiClient(baseUrl, apiKey).listEffects() } catch (_: Exception) {}
    }

    Column(Modifier.fillMaxWidth().padding(top = 8.dp)) {
        OutlinedTextField(value = prompt, onValueChange = { prompt = it },
            label = { Text("prompt do vídeo") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { aspect = "16:9" },
                colors = ButtonDefaults.outlinedButtonColors(contentColor = if (aspect == "16:9") Neon else Color.Gray)) { Text("16:9") }
            OutlinedButton(onClick = { aspect = "9:16" },
                colors = ButtonDefaults.outlinedButtonColors(contentColor = if (aspect == "9:16") Neon else Color.Gray)) { Text("9:16") }
            Text("720p travado p/ 2-3min (<5min)", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.align(Alignment.CenterVertically))
        }
        Text("duração (padrão 150s = 2.5min)", color = Color.Gray, fontSize = 11.sp)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            durations.forEach { d ->
                FilterChip(selected = duration == d, onClick = { duration = d },
                    label = { Text(if (d < 60) "${d}s" else if (d == 60) "1min" else "${d / 60}min${if (d % 60 > 0) " ${d % 60}s" else ""}") })
            }
        }
        Text("efeitos (${selectedFx.size}/5 — vazio = IA escolhe)", color = Color.Gray, fontSize = 11.sp)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            allFx.take(40).forEach { f ->
                val on = selectedFx.contains(f.id)
                FilterChip(selected = on, onClick = {
                    if (on) selectedFx.remove(f.id) else if (selectedFx.size < 5) selectedFx.add(f.id)
                }, label = { Text(f.label) })
            }
        }
        Button(enabled = !busy && prompt.isNotBlank(), onClick = {
            busy = true; progress = 0; previewUrl = null; videoFile = null
            scope.launch {
                try {
                    val api = ApiClient(baseUrl, apiKey)
                    // trava 720p p/ vídeo longo (motor rebaixa sozinho, mas já vamos no rápido)
                    lastRes = "720p"
                    var job = api.createVideo(prompt.trim(), aspect, lastRes, duration, selectedFx.toList())
                    status = "job ${job.jobId} · ${job.provider}"
                    while (job.status == "queued" || job.status == "generating") {
                        delay(2000)
                        job = api.getJob(job.jobId)
                        progress = job.progress
                        stage = "${job.stage ?: job.status} [${job.progress}%]" +
                            (job.frames?.let { " · $it/${job.totalFrames} quadros" } ?: "")
                        api.previewUrl(job, System.currentTimeMillis())?.let {
                            previewUrl = it; previewTick = System.currentTimeMillis()
                        }
                        status = "job ${job.jobId}\n$stage\nefeitos: ${job.effects.joinToString()}" +
                            if (job.fallbackUsed) "\nmodo: IA + efeitos (fallback local)" else "\nmodo: veo"
                    }
                    progress = 100
                    if (job.status == "completed") {
                        stage = "concluído — vídeo pronto"
                        val dest = File(ctx.cacheDir, "${job.jobId}.mp4")
                        api.downloadTo(job, dest)
                        videoFile = dest
                        status += "\n\nPRONTO: ${dest.absolutePath}"
                    } else {
                        stage = "falhou"
                        status += "\n\nfalhou: ${job.error ?: "desconhecido"}"
                    }
                } catch (e: Exception) {
                    stage = "erro"; status = "erro: ${e.message?.take(400)}"
                } finally { busy = false }
            }
        }, colors = ButtonDefaults.buttonColors(contentColor = Magenta)) { Text("GERAR VÍDEO ${duration}s") }
        LinearProgressIndicator(progress = { progress / 100f }, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
        Text(stage, color = Neon, fontSize = 12.sp)
        previewUrl?.let { url ->
            Text("RENDER AO VIVO", color = Magenta, fontSize = 10.sp)
            AsyncImage(model = url, contentDescription = "preview", modifier = Modifier.fillMaxWidth())
        }
        Text(status, color = Color.Gray, fontSize = 11.sp)
        videoFile?.let { f ->
            Text("player local: ${f.name}", color = Neon, fontSize = 12.sp)
            AndroidView(factory = {
                VideoView(it).apply {
                    setMediaController(MediaController(it).also { mc -> mc.setAnchorView(this) })
                    setVideoURI(Uri.fromFile(f))
                    requestFocus(); start()
                }
            }, modifier = Modifier.fillMaxWidth().height(220.dp))
        }
        if (previewTick < 0) Text("") // mantém recomposição do preview
    }
}
