package com.blackcore.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { MobileScreen() } }
    }
}

@Composable
private fun MobileScreen() {
    var endpoint by remember { mutableStateOf("https://") }
    var token by remember { mutableStateOf("") }
    var result by remember { mutableStateOf("Desconectado. Este app consulta apenas telemetria.") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("BLACKCORE", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
            Text("ULTIMATE // MOBILE", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(value = endpoint, onValueChange = { endpoint = it }, label = { Text("HTTPS do bridge no PC") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(value = token, onValueChange = { token = it }, label = { Text("Token de acesso") }, modifier = Modifier.fillMaxWidth(), singleLine = true, visualTransformation = PasswordVisualTransformation())
            Button(onClick = {
                val base = endpoint.trim().trimEnd('/')
                if (!base.startsWith("https://") || token.length < 32) {
                    result = "Use um endereço HTTPS válido e token de pelo menos 32 caracteres."
                } else {
                    busy = true
                    scope.launch {
                        result = try { fetchStatus(base, token) } catch (e: Exception) {
                            "Falha de conexão: " + (e.message ?: "erro desconhecido") + "\nConfira VPN/Wi-Fi, certificado confiável e token."
                        }
                        busy = false
                    }
                }
            }, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                Text(if (busy) "Conectando…" else "Conectar / atualizar")
            }
            HorizontalDivider()
            Text("STATUS DO PC", style = MaterialTheme.typography.titleMedium)
            Text(result)
            Text("Somente leitura nesta versão. Controle de tela, mouse, teclado e comandos remotos não estão habilitados.", style = MaterialTheme.typography.bodySmall)
        }
    }
}

private suspend fun fetchStatus(base: String, token: String): String = withContext(Dispatchers.IO) {
    val connection = URL("$base/api/status").openConnection() as HttpURLConnection
    try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 7000
        connection.readTimeout = 7000
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.setRequestProperty("Accept", "application/json")
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val body = stream.bufferedReader().use { it.readText() }
        if (code == 401) throw IllegalStateException("Token recusado (401).")
        if (code !in 200..299) throw IllegalStateException("HTTP $code")
        val json = JSONObject(body)
        val memory = json.optJSONObject("memory")
        val disk = json.optJSONObject("disk")
        val cpu = if (json.isNull("cpu_percent")) "N/D" else json.optDouble("cpu_percent").toString() + "%"
        val ram = memory?.optDouble("percent_used")?.toString()?.plus("%") ?: "N/D"
        val diskUse = disk?.optDouble("percent_used")?.toString()?.plus("%") ?: "N/D"
        "Conectado\nSistema: ${json.optString("platform", "N/D")}\nCPU: $cpu\nRAM: $ram\nDisco: $diskUse\n\nControle remoto: desativado\nComandos arbitrários: desativados"
    } finally {
        connection.disconnect()
    }
}
