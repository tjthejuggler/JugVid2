// Fix for HttpServerService.kt - Add this to the serve() method

// Add this case to the when statement in serve() method around line 340:
uri == "/data" && method == Method.GET -> handleGetData()

// Add this method to the IMUHttpServer inner class:
private fun handleGetData(): Response {
    return try {
        val imuService = imuDataService
        if (imuService == null) {
            return newFixedLengthResponse(
                Response.Status.INTERNAL_ERROR,
                MIME_PLAINTEXT,
                "IMU service not available"
            )
        }

        // Get the most recent recording file
        val recordingsDir = File(getExternalFilesDir(null), "recordings")
        if (!recordingsDir.exists()) {
            return newFixedLengthResponse(
                Response.Status.NOT_FOUND,
                "application/json",
                "[]"
            )
        }

        val csvFiles = recordingsDir.listFiles { file -> 
            file.name.endsWith(".csv") && file.name.startsWith("imu_")
        }?.sortedByDescending { it.lastModified() }

        if (csvFiles.isNullOrEmpty()) {
            return newFixedLengthResponse(
                Response.Status.OK,
                "application/json",
                "[]"
            )
        }

        // Read the most recent CSV file and convert to JSON
        val mostRecentFile = csvFiles.first()
        val jsonData = convertCsvToJson(mostRecentFile)

        newFixedLengthResponse(
            Response.Status.OK,
            "application/json",
            jsonData
        )
    } catch (e: Exception) {
        Log.e(TAG, "Error getting data", e)
        newFixedLengthResponse(
            Response.Status.INTERNAL_ERROR,
            MIME_PLAINTEXT,
            "Error: ${e.message}"
        )
    }
}

// Add this helper method to convert CSV to JSON:
private fun convertCsvToJson(csvFile: File): String {
    val readings = mutableListOf<Map<String, Any>>()
    
    try {
        csvFile.bufferedReader().use { reader ->
            var isHeader = true
            var isMetadata = true
            
            reader.forEachLine { line ->
                when {
                    line.startsWith("#") -> {
                        // Skip metadata lines
                        isMetadata = true
                    }
                    isHeader && !isMetadata -> {
                        // Skip CSV header
                        isHeader = false
                    }
                    !line.trim().isEmpty() && !isMetadata -> {
                        // Parse data line
                        val parts = line.split(",")
                        if (parts.size >= 7) {
                            val reading = mapOf(
                                "timestamp" to parts[0].toLongOrNull() ?: 0L,
                                "accel_x" to parts[1].toDoubleOrNull() ?: 0.0,
                                "accel_y" to parts[2].toDoubleOrNull() ?: 0.0,
                                "accel_z" to parts[3].toDoubleOrNull() ?: 0.0,
                                "gyro_x" to parts[4].toDoubleOrNull() ?: 0.0,
                                "gyro_y" to parts[5].toDoubleOrNull() ?: 0.0,
                                "gyro_z" to parts[6].toDoubleOrNull() ?: 0.0,
                                "mag_x" to if (parts.size > 7) parts[7].toDoubleOrNull() ?: 0.0 else 0.0,
                                "mag_y" to if (parts.size > 8) parts[8].toDoubleOrNull() ?: 0.0 else 0.0,
                                "mag_z" to if (parts.size > 9) parts[9].toDoubleOrNull() ?: 0.0 else 0.0
                            )
                            readings.add(reading)
                        }
                    }
                }
                
                if (isHeader && !line.startsWith("#")) {
                    isMetadata = false
                }
            }
        }
    } catch (e: Exception) {
        Log.e(TAG, "Error reading CSV file: ${csvFile.name}", e)
    }
    
    // Convert to JSON string
    return buildString {
        append("[")
        readings.forEachIndexed { index, reading ->
            if (index > 0) append(",")
            append("{")
            reading.entries.forEachIndexed { entryIndex, entry ->
                if (entryIndex > 0) append(",")
                append("\"${entry.key}\":${entry.value}")
            }
            append("}")
        }
        append("]")
    }
}

// Also add these imports to the top of HttpServerService.kt:
import java.io.File