package com.netzack.videos

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class DirectAITest {
    @Test
    fun detectByKeyOnly() {
        assertEquals("google", DirectAI.detect("AIza123456789012345"))
        assertEquals("anthropic", DirectAI.detect("sk-ant-xyz"))
        assertEquals("openai", DirectAI.detect("sk-xyz"))
        try {
            DirectAI.detect("qualquer-coisa")
            fail("deveria rejeitar chave desconhecida")
        } catch (_: IllegalArgumentException) {
        }
    }

    @Test
    fun registryHidesMarketUrls() {
        assertTrue(DirectAI.ENDPOINTS.size >= 12)
        assertTrue(DirectAI.ENDPOINTS.any { it.id == "google" })
        assertTrue(DirectAI.ENDPOINTS.any { it.id == "groq" })
        assertTrue(DirectAI.ENDPOINTS.any { it.id == "deepseek" })
        assertTrue(DirectAI.ENDPOINTS.any { it.id == "openrouter" })
    }

    @Test
    fun chooseEndpointProbesAndFindsAnyKey() {
        val reachable = setOf("mistral", "perplexity")
        val ep = DirectAI.chooseEndpoint("chave-misteriosa-qualquer") { it.id in reachable }
        assertEquals("mistral", ep!!.id)
    }

    @Test
    fun chooseEndpointUsesPrefixHintFirst() {
        val order = mutableListOf<String>()
        val ep = DirectAI.chooseEndpoint("gsk_algo") { e ->
            order.add(e.id)
            e.id == "openai" // groq responde falso (não aceita), openai responde verdadeiro
        }
        assertEquals("openai", ep!!.id)
        assertEquals("groq", order.first()) // hint de prefixo veio primeiro
    }

    @Test
    fun normalizeStripsPrefix() {
        assertEquals("veo-3.1-generate-preview", DirectAI.normalize("models/veo-3.1-generate-preview"))
        assertEquals("gpt-4o", DirectAI.normalize("gpt-4o"))
    }

    @Test
    fun pickVideoPrefers31() {
        assertEquals(
            "veo-3.1-generate-preview",
            DirectAI.pickVideoModel(listOf("veo-2.0-generate-001", "veo-3.1-generate-preview"))
        )
    }

    @Test
    fun pickVideoWithoutVeoExplains() {
        try {
            DirectAI.pickVideoModel(listOf("gemini-2.5-flash"))
            fail("deveria falhar sem Veo")
        } catch (e: RuntimeException) {
            assertTrue(e.message!!.contains("Veo"))
        }
    }

    @Test
    fun pickChatUsesPriority() {
        assertEquals(
            "gemini-3.1-pro-preview",
            DirectAI.pickChatModel("google", listOf("gemini-2.5-flash", "gemini-3.1-pro-preview"))
        )
    }

    @Test
    fun splitDurationTenMinutesIntoVeoChunks() {
        val chunks = DirectAI.splitDuration(600, DirectAI.VEO_CHUNKS)
        assertEquals(75, chunks.size)
        assertTrue(chunks.all { it in DirectAI.VEO_CHUNKS })
        assertTrue(chunks.sum() >= 600)
        assertTrue(chunks.sum() - 600 <= 3)
    }

    @Test
    fun splitDurationShortAndOddValues() {
        assertEquals(listOf(4), DirectAI.splitDuration(4, DirectAI.VEO_CHUNKS))
        assertEquals(listOf(8), DirectAI.splitDuration(8, DirectAI.VEO_CHUNKS))
        val fifteen = DirectAI.splitDuration(15, DirectAI.VEO_CHUNKS)
        assertTrue(fifteen.all { it in DirectAI.VEO_CHUNKS })
        assertTrue(fifteen.sum() in 15..18)
        val thirty = DirectAI.splitDuration(30, DirectAI.VEO_CHUNKS)
        assertEquals(30, thirty.sum())
    }

    @Test
    fun splitDurationSoraOptions() {
        val chunks = DirectAI.splitDuration(120, DirectAI.SORA_CHUNKS)
        assertTrue(chunks.all { it in DirectAI.SORA_CHUNKS })
        assertEquals(120, chunks.sum())
    }

    @Test
    fun effectsEmbedded() {
        assertTrue(Effects.ALL.size >= 10)
    }
}
