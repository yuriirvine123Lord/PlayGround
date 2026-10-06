package com.netzack.videos

/** Mesma lógica do backend (providers.py::infer_provider) para identificar a IA automaticamente. */
object ProviderDetector {

    fun infer(apiKey: String, provider: String = "auto", baseUrl: String? = null): String {
        var explicit = provider.lowercase().trim()
        explicit = when (explicit) {
            "gemini", "google_genai", "google-gemini" -> "google"
            "openai-compatible", "compatible" -> "openai_compatible"
            else -> explicit
        }
        val allowed = setOf("auto", "google", "openai", "openai_compatible", "anthropic")
        require(explicit in allowed) { "provider inválido. Use auto, google, openai, anthropic ou openai_compatible." }
        if (explicit != "auto") return explicit

        val host = (baseUrl ?: "").lowercase()
        if ("generativelanguage.googleapis.com" in host || "aiplatform.googleapis.com" in host) return "google"
        if ("anthropic.com" in host) return "anthropic"
        if ("api.openai.com" in host) return "openai"

        val key = apiKey.trim()
        if (key.startsWith("AIza")) return "google"
        if (key.startsWith("sk-ant-")) return "anthropic"
        if (key.startsWith("sk-")) return "openai"

        throw IllegalArgumentException(
            "Não foi possível identificar esta chave. Informe provider e base_url explicitamente."
        )
    }

    fun redact(key: String): String {
        if (key.length <= 8) return "********"
        return "${key.take(4)}…${key.takeLast(4)}"
    }
}
