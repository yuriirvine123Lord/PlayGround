package com.netzack.videos

import org.junit.Assert.assertEquals
import org.junit.Test

class ProviderDetectorTest {
    @Test
    fun autoDetectByPrefix() {
        assertEquals("google", ProviderDetector.infer("AIza123456789012345"))
        assertEquals("anthropic", ProviderDetector.infer("sk-ant-xyz"))
        assertEquals("openai", ProviderDetector.infer("sk-xyz"))
    }

    @Test
    fun explicitWins() {
        assertEquals("google", ProviderDetector.infer("qualquer", "google"))
        assertEquals("openai_compatible", ProviderDetector.infer("abc", "openai_compatible", "https://x/v1"))
    }

    @Test
    fun effectsNotEmpty() {
        assert(Effects.ALL.size >= 10)
        assert(Effects.ALL[1].promptSuffix.contains("cinematic", ignoreCase = true))
    }
}
