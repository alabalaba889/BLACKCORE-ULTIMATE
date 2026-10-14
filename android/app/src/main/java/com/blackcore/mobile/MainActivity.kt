package com.blackcore.mobile

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.math.roundToInt

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
    var showToken by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf("Desconectado. O app consulta apenas telemetria.") }
    var busy by remember { mutableStateOf(false) }
    var connected by remember { mutableStateOf(false) }
    var autoRefresh by remember { mutableStateOf(false) }
    var remoteConsent by remember { mutableStateOf(false) }
    var remoteMessage by remember { mutableStateOf("Controle remoto desligado até ser habilitado no PC.") }
    var screenBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var mouseX by remember { mutableStateOf("500") }
    var mouseY by remember { mutableStateOf("400") }
    var remoteText by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    LaunchedEffect(connected, autoRefresh, endpoint, token) {
        if (connected && autoRefresh) {
            while (isActive) {
                delay(15000)
                try {
                    result = fetchStatus(endpoint.trim().trimEnd('/'), token.trim())
                } catch (e: Exception) {
                    connected = false
                    result = "Atualização automática falhou: " + (e.message ?: "erro desconhecido")
                    break
                }
            }
        }
    }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("BLACKCORE", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
            Text("ULTIMATE // MOBILE", style = MaterialTheme.typography.titleMedium)
            Text("Painel Android • somente leitura", style = MaterialTheme.typography.bodyMedium)
            OutlinedTextField(
                value = endpoint, onValueChange = { endpoint = it },
                label = { Text("HTTPS do bridge no PC") }, modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedTextField(
                value = token, onValueChange = { token = it },
                label = { Text("Token (mínimo 32 caracteres)") }, modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                visualTransformation = if (showToken) VisualTransformation.None else PasswordVisualTransformation(),
                trailingIcon = {
                    TextButton(onClick = { showToken = !showToken }) {
                        Text(if (showToken) "Ocultar" else "Mostrar")
                    }
                }
            )
            Button(onClick = {
                val base = endpoint.trim().trimEnd('/')
                val uri = runCatching { Uri.parse(base) }.getOrNull()
                val validUrl = uri != null && uri.scheme == "https" && !uri.host.isNullOrBlank() &&
                    uri.userInfo == null && uri.query == null && uri.fragment == null
                if (!validUrl || token.trim().length < 32) {
                    result = "Use um endereço HTTPS válido, sem usuário/senha/query, e token de pelo menos 32 caracteres."
                    connected = false
                } else {
                    busy = true
                    val requestedToken = token.trim()
                    scope.launch {
                        result = try {
                            fetchStatus(base, requestedToken).also { connected = true }
                        } catch (e: Exception) {
                            connected = false
                            "Falha: " + (e.message ?: "erro desconhecido") +
                                "\nConfira VPN/Wi-Fi, certificado confiável, endereço e token."
                        } finally {
                            busy = false
                        }
                    }
                }
            }, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                Text(if (busy) "Conectando…" else if (connected) "Atualizar telemetria" else "Conectar ao PC")
            }
            if (connected) {
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Checkbox(checked = autoRefresh, onCheckedChange = { autoRefresh = it })
                    Text("Atualizar telemetria automaticamente (15 s)")
                }
                OutlinedButton(onClick = {
                    token = ""
                    connected = false
                    autoRefresh = false
                    remoteConsent = false
                    screenBitmap = null
                    result = "Desconectado. O token foi removido desta tela."
                }, modifier = Modifier.fillMaxWidth()) { Text("Desconectar e apagar token") }
            }
            HorizontalDivider()
            Text("CONTROLE REMOTO OPCIONAL", style = MaterialTheme.typography.titleMedium)
            Text("Requer bridge Windows com --enable-remote-control, HTTPS confiável e pyautogui instalado. A captura é uma imagem estática, não vídeo.", style = MaterialTheme.typography.bodySmall)
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Checkbox(checked = remoteConsent, onCheckedChange = { remoteConsent = it })
                Text("Autorizo controlar este PC nesta sessão")
            }
            OutlinedButton(onClick = {
                if (!remoteConsent || !connected) {
                    remoteMessage = "Conecte e marque a autorização antes de solicitar a tela."
                } else {
                    scope.launch {
                        remoteMessage = try {
                            screenBitmap = fetchScreen(endpoint.trim().trimEnd('/'), token.trim())
                            "Captura recebida. A imagem não é vídeo ao vivo."
                        } catch (e: Exception) {
                            "Falha na captura: " + (e.message ?: "erro desconhecido")
                        }
                    }
                }
            }, enabled = connected && !busy, modifier = Modifier.fillMaxWidth()) { Text("Capturar tela do PC") }
            screenBitmap?.let { bitmap ->
                Image(bitmap = bitmap.asImageBitmap(), contentDescription = "Captura estática da tela do PC",
                    modifier = Modifier.fillMaxWidth())
            }
            OutlinedTextField(value = mouseX, onValueChange = { mouseX = it.take(6).filter(Char::isDigit) },
                label = { Text("Coordenada X") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(value = mouseY, onValueChange = { mouseY = it.take(6).filter(Char::isDigit) },
                label = { Text("Coordenada Y") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedButton(onClick = {
                sendRemoteAction(remoteConsent, connected, endpoint, token, JSONObject()
                    .put("action", "move").put("x", mouseX.toIntOrNull() ?: -1).put("y", mouseY.toIntOrNull() ?: -1),
                    scope, { remoteMessage = it })
            }, modifier = Modifier.fillMaxWidth()) { Text("Mover mouse") }
            OutlinedButton(onClick = {
                sendRemoteAction(remoteConsent, connected, endpoint, token, JSONObject()
                    .put("action", "click").put("button", "left")
                    .put("x", mouseX.toIntOrNull() ?: -1).put("y", mouseY.toIntOrNull() ?: -1),
                    scope, { remoteMessage = it })
            }, modifier = Modifier.fillMaxWidth()) { Text("Clique esquerdo") }
            OutlinedTextField(value = remoteText, onValueChange = { remoteText = it.take(300) },
                label = { Text("Texto a digitar (máx. 300)") }, modifier = Modifier.fillMaxWidth())
            OutlinedButton(onClick = {
                if (remoteText.isBlank()) remoteMessage = "Informe um texto antes de enviar."
                else sendRemoteAction(remoteConsent, connected, endpoint, token,
                    JSONObject().put("action", "type").put("text", remoteText),
                    scope, { remoteMessage = it })
            }, modifier = Modifier.fillMaxWidth()) { Text("Digitar texto") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(onClick = {
                    sendRemoteAction(remoteConsent, connected, endpoint, token,
                        JSONObject().put("action", "key").put("key", "enter"),
                        scope, { remoteMessage = it })
                }, modifier = Modifier.weight(1f)) { Text("Enter") }
                OutlinedButton(onClick = {
                    sendRemoteAction(remoteConsent, connected, endpoint, token,
                        JSONObject().put("action", "key").put("key", "esc"),
                        scope, { remoteMessage = it })
                }, modifier = Modifier.weight(1f)) { Text("Esc") }
            }
            Text(remoteMessage, style = MaterialTheme.typography.bodySmall)
            HorizontalDivider()
            Text("STATUS DO PC", style = MaterialTheme.typography.titleMedium)
            Text(result, style = MaterialTheme.typography.bodyMedium)
            Text(
                "Segurança: o token fica apenas na memória da tela. Não há armazenamento persistente, controle de tela, mouse/teclado ou execução remota nesta versão.",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

private fun sendRemoteAction(
    consent: Boolean,
    connected: Boolean,
    endpoint: String,
    token: String,
    payload: JSONObject,
    scope: kotlinx.coroutines.CoroutineScope,
    report: (String) -> Unit
) {
    if (!consent || !connected) {
        report("Conecte ao PC e marque a autorização antes de enviar ações.")
        return
    }
    if (!endpoint.trim().startsWith("https://") || token.trim().length < 32) {
        report("O controle remoto exige HTTPS e token válido.")
        return
    }
    scope.launch {
        report("Enviando ação autorizada…")
        try {
            report(postRemoteAction(endpoint.trim().trimEnd('/'), token.trim(), payload))
        } catch (e: Exception) {
            report("Ação recusada ou falhou: " + (e.message ?: "erro desconhecido"))
        }
    }
}

private suspend fun postRemoteAction(base: String, token: String, payload: JSONObject): String = withContext(Dispatchers.IO) {
    val connection = URL("$base/api/control").openConnection() as HttpURLConnection
    try {
        connection.requestMethod = "POST"
        connection.connectTimeout = 7000
        connection.readTimeout = 7000
        connection.instanceFollowRedirects = false
        connection.doOutput = true
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        connection.setRequestProperty("X-Blackcore-Confirm", "YES")
        val bytes = payload.toString().toByteArray(Charsets.UTF_8)
        connection.outputStream.use { it.write(bytes) }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        if (code !in 200..299) {
            val reason = runCatching { JSONObject(body).optString("error") }.getOrDefault("HTTP $code")
            throw IllegalStateException("$reason (HTTP $code)")
        }
        "Ação enviada: " + payload.optString("action")
    } finally {
        connection.disconnect()
    }
}

private suspend fun fetchScreen(base: String, token: String): Bitmap = withContext(Dispatchers.IO) {
    val connection = URL("$base/api/screen.jpg").openConnection() as HttpURLConnection
    try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 7000
        connection.readTimeout = 7000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.setRequestProperty("Accept", "image/jpeg")
        val code = connection.responseCode
        if (code !in 200..299) {
            val body = connection.errorStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            val reason = runCatching { JSONObject(body).optString("error") }.getOrDefault("HTTP $code")
            throw IllegalStateException("$reason (HTTP $code)")
        }
        connection.inputStream.use { input ->
            BitmapFactory.decodeStream(input) ?: throw IllegalStateException("Imagem de tela inválida.")
        }
    } finally {
        connection.disconnect()
    }
}

private suspend fun fetchStatus(base: String, token: String): String = withContext(Dispatchers.IO) {
    val started = System.nanoTime()
    val connection = URL("$base/api/status").openConnection() as HttpURLConnection
    try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 7000
        connection.readTimeout = 7000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.setRequestProperty("Accept", "application/json")
        val code = connection.responseCode
        if (code == 401) throw IllegalStateException("Token recusado (401).")
        if (code !in 200..299) throw IllegalStateException("Resposta HTTP $code.")
        val body = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        val json = JSONObject(body)
        val memory = json.optJSONObject("memory")
        val disk = json.optJSONObject("disk")
        val network = json.optJSONObject("network")
        val cpu = if (json.isNull("cpu_percent")) "N/D" else "%.1f%%".format(json.optDouble("cpu_percent"))
        val ram = memory?.let { "%.1f%% (%s / %s)".format(it.optDouble("percent_used"), bytes(it.optLong("used_bytes")), bytes(it.optLong("total_bytes"))) } ?: "N/D"
        val availableRam = memory?.let { bytes(it.optLong("available_bytes")) } ?: "N/D"
        val diskUse = disk?.let { "%.1f%% (%s usados; %s livres)".format(it.optDouble("percent_used"), bytes(it.optLong("used_bytes")), bytes(it.optLong("free_bytes"))) } ?: "N/D"
        val sent = network?.let { bytes(it.optLong("bytes_sent")) } ?: "N/D"
        val received = network?.let { bytes(it.optLong("bytes_received")) } ?: "N/D"
        val processes = if (json.isNull("process_count")) "N/D" else json.optInt("process_count").toString()
        val cores = if (json.isNull("cpu_count")) "N/D" else json.optInt("cpu_count").toString()
        val uptime = duration(json.optLong("uptime_seconds", -1))
        val battery = json.optJSONObject("battery")?.let {
            it.optInt("percent").toString() + "%" + if (it.optBoolean("plugged")) " (carregando)" else ""
        } ?: "N/D"
        val latency = (System.nanoTime() - started) / 1_000_000
        "CONECTADO • somente leitura\nSistema: ${json.optString("platform", "N/D")}\nCPU: $cpu\nRAM usada: $ram\nRAM disponível: $availableRam\nDisco: $diskUse\nRede enviada: $sent\nRede recebida: $received\nProcessos: $processes\nNúcleos lógicos: $cores\nTempo ligado: $uptime\nBateria: $battery\nLatência: ${latency} ms\nBridge ativo: ${duration(json.optLong("bridge_uptime_seconds", -1))}"
    } finally {
        connection.disconnect()
    }
}

private fun bytes(value: Long): String {
    if (value < 0) return "N/D"
    val units = arrayOf("B", "KB", "MB", "GB", "TB")
    var amount = value.toDouble()
    var unit = 0
    while (amount >= 1024 && unit < units.lastIndex) { amount /= 1024; unit++ }
    return if (unit == 0) "${amount.roundToInt()} ${units[unit]}" else "%.1f %s".format(amount, units[unit])
}

private fun duration(seconds: Long): String {
    if (seconds < 0) return "N/D"
    val days = seconds / 86400
    val hours = (seconds % 86400) / 3600
    val minutes = (seconds % 3600) / 60
    return (if (days > 0) "${days}d " else "") + "${hours}h ${minutes}m"
}
