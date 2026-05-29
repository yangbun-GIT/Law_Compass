package com.lawcompass.mobiletest

import android.graphics.BitmapFactory
import android.util.Base64
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions
import kotlin.math.max

@CapacitorPlugin(name = "MlKitObjectDetector")
class MlKitObjectDetectorPlugin : Plugin() {
    @PluginMethod
    fun detectObjects(call: PluginCall) {
        val dataUrl = call.getString("imageDataUrl")
        if (dataUrl.isNullOrBlank()) {
            call.reject("imageDataUrl is required")
            return
        }

        val base64 = dataUrl.substringAfter(",", dataUrl)
        val bytes = try {
            Base64.decode(base64, Base64.DEFAULT)
        } catch (exc: Exception) {
            call.reject("invalid imageDataUrl")
            return
        }

        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        if (bitmap == null) {
            call.reject("image decode failed")
            return
        }

        val options = ObjectDetectorOptions.Builder()
            .setDetectorMode(ObjectDetectorOptions.SINGLE_IMAGE_MODE)
            .enableMultipleObjects()
            .enableClassification()
            .build()

        val detector = ObjectDetection.getClient(options)
        val startedAt = System.currentTimeMillis()
        val image = InputImage.fromBitmap(bitmap, 0)

        detector.process(image)
            .addOnSuccessListener { detectedObjects ->
                val objects = JSArray()
                detectedObjects.forEach { detected ->
                    val box = detected.boundingBox
                    val labels = JSArray()
                    detected.labels.forEach { label ->
                        labels.put(JSObject().apply {
                            put("text", label.text)
                            put("confidence", label.confidence)
                            put("index", label.index)
                        })
                    }

                    objects.put(JSObject().apply {
                        put("trackingId", detected.trackingId)
                        put("labels", labels)
                        put("boundingBox", JSObject().apply {
                            put("left", box.left)
                            put("top", box.top)
                            put("right", box.right)
                            put("bottom", box.bottom)
                            put("width", max(0, box.width()))
                            put("height", max(0, box.height()))
                        })
                    })
                }

                call.resolve(JSObject().apply {
                    put("frameIndex", call.getInt("frameIndex", 0))
                    put("frameTimeSec", call.getDouble("frameTimeSec", 0.0))
                    put("processingMs", System.currentTimeMillis() - startedAt)
                    put("width", bitmap.width)
                    put("height", bitmap.height)
                    put("objects", objects)
                })
            }
            .addOnFailureListener { exc ->
                call.reject("ML Kit object detection failed", exc)
            }
    }
}
