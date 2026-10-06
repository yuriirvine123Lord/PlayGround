package com.netzack.videos

/** Presets de efeitos especiais estilo Veo 3 — viram sufixos de prompt + parâmetros. */
data class EffectPreset(
    val name: String,
    val promptSuffix: String,
    val negativePrompt: String = "blurry, low quality, distorted, watermark, text on screen",
    val resolution: String = "720p"
)

object Effects {
    val ALL = listOf(
        EffectPreset("Original (sem efeito)", ""),
        EffectPreset(
            "Cinema Épico Veo3",
            ", epic cinematic lighting, anamorphic lens flare, shallow depth of field, 24fps film grain, dramatic color grade, surround ambience"
        ),
        EffectPreset(
            "Neon Noite Chuvosa",
            ", rain-soaked neon street at night, slow dolly forward, realistic wet reflections, distant traffic and gentle rain sound, cyberpunk glow"
        ),
        EffectPreset(
            "Drone Aéreo",
            ", sweeping aerial drone shot, slow push-in from high altitude, volumetric clouds, wide landscape, natural wind sound"
        ),
        EffectPreset(
            "Slow Motion 120fps",
            ", ultra slow motion 120fps, floating dust particles, detailed motion blur, soft ambient sound design"
        ),
        EffectPreset(
            "Anime Cinematográfico",
            ", anime cinematic style, vibrant cel shading, dynamic camera pan, expressive lighting, stylized sound effects"
        ),
        EffectPreset(
            "Sci-Fi Holográfico",
            ", futuristic sci-fi hologram overlay, glowing particles, blue volumetric light, high-tech hum sound"
        ),
        EffectPreset(
            "Retrô VHS Anos 80",
            ", retro VHS 80s look, tracking lines, warm grain, nostalgic synth ambience, slight chromatic aberration"
        ),
        EffectPreset(
            "Terror Atmosférico",
            ", dark atmospheric horror, fog, flickering practical lights, slow creeping dolly, tense low drone sound"
        ),
        EffectPreset(
            "Natureza Macro",
            ", extreme macro nature shot, morning dew, bokeh background, gentle birds and leaves ambience"
        ),
        EffectPreset(
            "Ação + Zoom Dinâmico",
            ", fast action scene, dynamic crash zoom and whip pan, motion energy, punchy cinematic SFX"
        )
    )
}
