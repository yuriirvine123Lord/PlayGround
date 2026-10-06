package com.netzack.videos

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

/**
 * Une os pedaços gerados (ex.: 10 min = 75 clips de 8 s) em um único MP4.
 * Usa MediaExtractor + MediaMuxer da própria Android. Se falhar, o app toca
 * os pedaços em sequência (fallback no MainActivity).
 */
object VideoStitcher {

    fun concat(inputs: List<File>, output: File): Boolean {
        if (inputs.isEmpty()) return false
        if (inputs.size == 1) {
            return try {
                inputs[0].copyTo(output, overwrite = true)
                true
            } catch (_: Exception) {
                false
            }
        }
        return try {
            val muxer = MediaMuxer(output.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            var started = false
            var videoTrackId = -1
            var audioTrackId = -1
            var baseTimeUs = 0L

            for (f in inputs) {
                if (!f.exists()) continue
                val ex = MediaExtractor()
                ex.setDataSource(f.absolutePath)
                var vIdx = -1
                var aIdx = -1
                for (i in 0 until ex.trackCount) {
                    val mime = ex.getTrackFormat(i).getString(MediaFormat.KEY_MIME) ?: continue
                    if (vIdx < 0 && mime.startsWith("video/")) vIdx = i
                    if (aIdx < 0 && mime.startsWith("audio/")) aIdx = i
                }
                if (vIdx < 0) {
                    ex.release()
                    continue
                }

                if (!started) {
                    videoTrackId = muxer.addTrack(ex.getTrackFormat(vIdx))
                    if (aIdx >= 0) audioTrackId = muxer.addTrack(ex.getTrackFormat(aIdx))
                    muxer.start()
                    started = true
                }

                ex.selectTrack(vIdx)
                if (aIdx >= 0) ex.selectTrack(aIdx)

                val fmt = ex.getTrackFormat(vIdx)
                val cap = if (fmt.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                    fmt.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE)
                } else {
                    0
                }
                val buf = ByteBuffer.allocate(if (cap > 0) cap + 1024 else 8 * 1024 * 1024)
                val info = MediaCodec.BufferInfo()
                var maxEnd = baseTimeUs

                while (true) {
                    buf.clear()
                    val size = ex.readSampleData(buf, 0)
                    if (size < 0) break
                    val t = ex.getSampleTime()
                    if (t < 0) break
                    val trackIdx = ex.getSampleTrackIndex()
                    val outTrack = when (trackIdx) {
                        vIdx -> videoTrackId
                        aIdx -> audioTrackId
                        else -> -1
                    }
                    if (outTrack >= 0) {
                        info.offset = 0
                        info.size = size
                        info.presentationTimeUs = baseTimeUs + t
                        val sync = ex.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC != 0
                        info.flags = if (sync) MediaCodec.BUFFER_FLAG_KEY_FRAME else 0
                        muxer.writeSampleData(outTrack, buf, info)
                    }
                    val end = baseTimeUs + t
                    if (end > maxEnd) maxEnd = end
                    if (!ex.advance()) break
                }

                baseTimeUs = maxEnd + 33_333L // ~30 fps de folga entre pedaços
                ex.release()
            }

            if (started) muxer.stop()
            muxer.release()
            output.exists() && output.length() > 0
        } catch (_: Exception) {
            try {
                output.delete()
            } catch (_: Exception) {
            }
            false
        }
    }
}
