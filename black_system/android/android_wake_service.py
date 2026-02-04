"""
Android Wake Service
===================

功能：
Android端的唤醒服务
提供多模态唤醒能力

注意：这是Android原生代码的参考实现
实际使用时需要转换为Kotlin/Java

作者：Matrix Agent
版本：1.0.0
日期：2026-02-04
"""

# ============================================
# 参考实现 - Android Kotlin代码模板
# ============================================

KOTLIN_WAKE_SERVICE_TEMPLATE = '''
package com.black.system.wake

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Build
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import kotlinx.coroutines.*
import java.util.*

/**
 * BLACK Wake Service - Android唤醒服务
 * 
 * 功能：
 * 1. 语音唤醒检测
 * 2. 悬浮窗快捷面板
 * 3. 跨设备唤醒
 */
class BlackWakeService : AccessibilityService() {

    companion object {
        private const val TAG = "BlackWake"
        private const val WAKR_WORD = "嘿BLACK"
        const val ACTION_WAKE = "com.black.system.WAKE"
        const val EXTRA_COMMAND = "command"
    }

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var speechRecognizer: SpeechRecognizer? = null
    private var floatingPanel: FloatingPanel? = null
    private var isListening = false

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "BlackWakeService created")
        initSpeechRecognizer()
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "Service connected")
        showFloatingWindow()
    }

    private fun initSpeechRecognizer() {
        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                setRecognitionListener(createRecognitionListener())
            }
        }
    }

    private fun createRecognitionListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                isListening = true
                Log.d(TAG, "Ready for speech")
            }

            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}

            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {
                isListening = false
            }

            override fun onError(error: Int) {
                isListening = false
                // 重新开始监听
                startListening()
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val command = matches?.firstOrNull() ?: ""
                
                if (command.isNotEmpty()) {
                    processCommand(command)
                }
                
                // 继续监听
                startListening()
            }

            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    private fun startListening() {
        if (!isListening && speechRecognizer != null) {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            speechRecognizer?.startListening(intent)
        }
    }

    private fun processCommand(command: String) {
        Log.d(TAG, "Processing command: $command")
        
        // 检测唤醒词
        if (command.contains(WAKR_WORD) || command.contains("小黑")) {
            val cleanCommand = command
                .replace(WAKR_WORD, "")
                .replace("小黑", "")
                .trim()
            
            if (cleanCommand.isNotEmpty()) {
                executeCommand(cleanCommand)
            } else {
                // 显示等待指示
                showListeningState()
            }
        }
    }

    private fun executeCommand(command: String) {
        // 发送到BLACK Core
        serviceScope.launch {
            try {
                val response = BlackApiClient.wakeSystem(command)
                if (response.success) {
                    showSuccessFeedback()
                } else {
                    showErrorFeedback()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Execute command failed", e)
                showErrorFeedback()
            }
        }
    }

    private fun showFloatingWindow() {
        if (floatingPanel == null) {
            floatingPanel = FloatingPanel(this)
        }
        floatingPanel?.show()
    }

    private fun showListeningState() {
        floatingPanel?.showListeningState()
    }

    private fun showSuccessFeedback() {
        floatingPanel?.showSuccess()
    }

    private fun showErrorFeedback() {
        floatingPanel?.showError()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        speechRecognizer?.destroy()
        floatingPanel?.dismiss()
    }
}
'''

KOTLIN_FLOATING_PANEL_TEMPLATE = '''
package com.black.system.ui

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

/**
 * BLACK Floating Panel - 统一控制悬浮窗
 */
class FloatingPanel(context: Context) : LinearLayout(context) {

    private val windowManager: WindowManager
    private var isExpanded = false
    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    init {
        orientation = VERTICAL
        setBackgroundColor(0xCC1E293B.toInt())
        setPadding(32, 32, 32, 32)
        
        windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        
        setupViews()
    }

    private fun setupViews() {
        // 状态指示器
        val statusIndicator = View(context).apply {
            layoutParams = LayoutParams(32, 32)
            setBackgroundColor(0x22C55E.toInt()) // 绿色表示在线
        }
        addView(statusIndicator)

        // 标题
        val title = TextView(context).apply {
            text = "BLACK System"
            textSize = 14f
            setTextColor(0xFFFFFFFF.toInt())
        }
        addView(title)

        // 点击展开面板
        setOnClickListener {
            if (!isExpanded) {
                expand()
            }
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupDrag() {
        setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - initialTouchX).toInt()
                    val dy = (event.rawY - initialTouchY).toInt()
                    params.x = initialX + dx
                    params.y = initialY + dy
                    windowManager.updateViewLayout(this, params)
                    true
                }
                else -> false
            }
        }
    }

    private val params: WindowManager.LayoutParams
        get() = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 100
            y = 300
        }

    fun show() {
        try {
            windowManager.addView(this, params)
        } catch (e: Exception) {
            Log.e("FloatingPanel", "Show failed", e)
        }
    }

    fun dismiss() {
        try {
            windowManager.removeView(this)
        } catch (e: Exception) {
            Log.e("FloatingPanel", "Dismiss failed", e)
        }
    }

    fun expand() {
        // 展开为完整面板
        isExpanded = true
        // 添加更多控件...
    }

    fun collapse() {
        // 折叠为最小形式
        isExpanded = false
        // 移除额外控件...
    }

    fun showListeningState() {
        // 显示正在聆听
    }

    fun showSuccess() {
        // 显示成功反馈
    }

    fun showError() {
        // 显示错误反馈
    }
}
'''

KOTLIN_API_CLIENT_TEMPLATE = '''
package com.black.system.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

/**
 * BLACK API Client - Android端API客户端
 */
object BlackApiClient {

    private const val BASE_URL = "http://192.168.1.100:9001" // Windows PC IP
    private val jsonMediaType = "application/json".toMediaType()
    private val client = OkHttpClient()

    /**
     * 唤醒系统执行命令
     */
    suspend fun wakeSystem(command: String): WakeResponse = withContext(Dispatchers.IO) {
        try {
            val json = JSONObject().apply {
                put("command", command)
                put("source", "android")
                put("mode", "voice")
            }

            val request = Request.Builder()
                .url("$BASE_URL/api/wake")
                .post(json.toString().toRequestBody(jsonMediaType))
                .build()

            client.newCall(request).execute().use { response ->
                val body = response.body?.string() ?: "{}"
                val result = JSONObject(body)
                
                WakeResponse(
                    success = result.optBoolean("success", false),
                    taskId = result.optString("task_id", ""),
                    message = result.optString("message", "")
                )
            }
        } catch (e: IOException) {
            WakeResponse(success = false, message = "Network error: ${e.message}")
        } catch (e: Exception) {
            WakeResponse(success = false, message = "Error: ${e.message}")
        }
    }

    /**
     * 获取系统状态
     */
    suspend fun getStatus(): SystemStatus = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/status")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                val body = response.body?.string() ?: "{}"
                val result = JSONObject(body)
                
                SystemStatus(
                    running = result.optBoolean("running", false),
                    agentsOnline = result.optInt("agents_online", 0),
                    tasksPending = result.optInt("tasks_pending", 0)
                )
            }
        } catch (e: Exception) {
            SystemStatus()
        }
    }

    /**
     * 获取Agent列表
     */
    suspend fun getAgents(): List<AgentInfo> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/agents")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                val body = response.body?.string() ?: "[]"
                val result = JSONObject(body)
                val agentsArray = result.optJSONArray("agents") ?: return@withContext emptyList()
                
                (0 until agentsArray.length()).map { i ->
                    val agentJson = agentsArray.getJSONObject(i)
                    AgentInfo(
                        id = agentJson.optString("id", ""),
                        name = agentJson.optString("name", ""),
                        type = agentJson.optString("type", ""),
                        status = agentJson.optString("status", "")
                    )
                }
            }
        } catch (e: Exception) {
            emptyList()
        }
    }
}

data class WakeResponse(
    val success: Boolean,
    val taskId: String = "",
    val message: String = ""
)

data class SystemStatus(
    val running: Boolean = false,
    val agentsOnline: Int = 0,
    val tasksPending: Int = 0
)

data class AgentInfo(
    val id: String,
    val name: String,
    val type: String,
    val status: String
)
'''

# ============================================
# Python后端服务（模拟Android唤醒接收）
# ============================================

import asyncio
from typing import Dict, Any
from datetime import datetime

class AndroidWakeReceiver:
    """
    Android唤醒接收器
    
    接收来自Android设备的唤醒请求
    """
    
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.registered_devices: Dict[str, Dict] = {}
    
    async def register_device(self, device_id: str, info: Dict) -> bool:
        """注册Android设备"""
        self.registered_devices[device_id] = {
            **info,
            "registered_at": datetime.now().isoformat()
        }
        return True
    
    async def handle_wake(self, device_id: str, command: str) -> Dict[str, Any]:
        """处理唤醒请求"""
        if device_id not in self.registered_devices:
            return {"success": False, "error": "Device not registered"}
        
        # 发送到调度器
        from ..core.main import TaskRequest, TaskPriority
        
        task_request = TaskRequest(
            task_type="general",
            description=command,
            priority=TaskPriority.HIGH,
            source=f"android:{device_id}"
        )
        
        task_id = await self.scheduler.dispatch(task_request)
        
        return {
            "success": True,
            "task_id": task_id,
            "device_id": device_id,
            "command": command
        }
    
    async def send_push_notification(self, device_id: str, title: str, 
                                   body: str) -> bool:
        """
        发送推送通知到Android设备
        （实际实现需要Firebase Cloud Messaging）
        """
        print(f"📱 Push to {device_id}: {title} - {body}")
        return True


# 使用示例
if __name__ == "__main__":
    print("Android Wake Service Reference Implementation")
    print("\n主要组件：")
    print("1. BlackWakeService - 语音唤醒服务")
    print("2. FloatingPanel - 悬浮窗控制面板")
    print("3. BlackApiClient - API客户端")
    print("\n需要在Android Studio中实现为Kotlin代码")
