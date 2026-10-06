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
    fun effectsEmbedded() {
        assertTrue(Effects.ALL.size >= 10)
    }
}
