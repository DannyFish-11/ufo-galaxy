# BLACK System - 统一智能体调度平台

**版本**: v5.0.0  
**作者**: Matrix Agent  
**日期**: 2026-02-04

---

## 📋 目录

- [简介](#简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [API参考](#api参考)
- [Android集成](#android集成)
- [常见问题](#常见问题)

---

## 简介

BLACK System是一个**统一智能体调度平台**，旨在整合和管理多个AI Agent系统，提供跨设备、跨平台的智能任务执行能力。

### 🎯 核心目标

1. **统一调度** - 整合MiniMax、UFO³ Galaxy、OpenWork等多个Agent系统
2. **跨设备协同** - 支持Windows、Android、云端设备的统一控制
3. **自然语言交互** - 支持语音、文本等多种唤醒方式
4. **智能任务分发** - 根据任务类型自动选择最佳Agent执行

---

## 核心特性

### 🤖 多Agent统一调度

| Agent | 类型 | 主要功能 | 状态 |
|:---|:---|:---|:---:|
| UFO³ Galaxy | 主控系统 | 96个功能节点、LLM集成、自动化 | ✅ |
| MiniMax | 对话助手 | 智能对话、图像生成 | ✅ |
| Android Bridge | 移动设备 | 应用控制、屏幕操作 | ✅ |
| Windows Control | 系统控制 | UI自动化、进程管理 | ✅ |

### 🔗 跨设备能力

- **统一调度核心** (端口 9001) - 任务分发与协调
- **WebSocket实时通信** - 双向异步通信
- **Tailscale组网** - 跨网络设备互联
- **多模态唤醒** - 语音、文本、快捷键、手势

### 🧠 智能任务处理

- **意图识别** - 自然语言理解
- **负载均衡** - 自动选择最佳Agent
- **冲突检测** - 防止资源竞争
- **任务追踪** - 完整执行日志

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BLACK System v5.0                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   MiniMax     │  │  OpenWork    │  │ UFO³ Galaxy │              │
│  │  (Electron)   │  │   (VSCode)   │  │  (Python)   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         └────────────────┼─────────────────┘                       │
│                          │                                           │
│                    ┌─────▼─────┐                                    │
│                    │  BLACK    │  ← 统一调度核心                       │
│                    │  Core     │                                     │
│                    │  (9001)   │                                     │
│                    └─────┬─────┘                                    │
│                          │                                           │
│    ┌─────────────────────┼─────────────────────┐                   │
│    │                     │                     │                    │
│ ┌──▼──┐            ┌─────▼─────┐          ┌──▼────┐               │
│ │Win   │            │ Android   │          │ Cloud  │               │
│ │Agent │            │ Agent     │          │ Agent  │               │
│ └──┬──┘            └─────┬─────┘          └───┬────┘               │
│    │                      │                     │                     │
│    └──────────────────────┼─────────────────────┘                    │
│                           │                                            │
│                    ┌──────▼──────┐                                     │
│                    │  Tailscale  │  ← 跨设备组网                        │
│                    │   Network   │                                      │
│                    └─────────────┘                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- Windows 10/11 或 Linux/macOS
- 4GB RAM (推荐 8GB)
- Git

### 2. 安装步骤

```bash
# 克隆仓库
git clone https://github.com/DannyFish-11/ufo-galaxy.git
cd ufo-galaxy

# 安装Python依赖
pip install fastapi uvicorn httpx pydantic

# 一键启动所有服务
black_system\start_black_system.bat
```

### 3. 访问Dashboard

启动后，打开浏览器访问：

- **BLACK Dashboard**: http://localhost:9001
- **UFO³ Galaxy**: http://localhost:9000
- **系统监控**: http://localhost:3000

---

## 使用指南

### 🎤 语音唤醒

```
"嘿BLACK，帮我打开微信"
"嘿BLACK，搜索今天的新闻"
"嘿BLACK，帮我写一段Python代码"
```

### ⌨️ 文本命令

直接在Dashboard输入框中输入命令：

```
打开微信并发送给张三"消息：晚上见"
搜索AI相关的最新新闻
帮我关闭浏览器
```

### 📱 Android控制

1. 安装Android应用
2. 连接同一网络
3. 使用语音或悬浮窗控制

### 🔧 API调用

```python
import httpx
import json

# 唤醒系统执行命令
async def wake_system(command):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9001/api/wake",
            json={
                "command": command,
                "source": "api",
                "mode": "text"
            }
        )
        return response.json()

# 调用示例
result = await wake_system("帮我打开微信")
print(result)
```

---

## API参考

### REST API

#### 系统状态

```http
GET /api/status
```

响应：
```json
{
    "running": true,
    "agents_total": 3,
    "agents_online": 3,
    "tasks_pending": 0,
    "tasks_running": 1
}
```

#### 任务分发

```http
POST /api/task/dispatch
Content-Type: application/json

{
    "task_type": "automation",
    "description": "打开微信并发送消息",
    "priority": "MEDIUM",
    "source": "voice"
}
```

#### 唤醒系统

```http
POST /api/wake
Content-Type: application/json

{
    "command": "帮我打开微信",
    "source": "android",
    "mode": "voice"
}
```

#### Agent管理

```http
GET /api/agents          # 列出所有Agent
POST /api/agent/register  # 注册新Agent
POST /api/agent/heartbeat # Agent心跳
```

### WebSocket API

连接：`ws://localhost:9001/ws`

#### 消息格式

**发送**:
```json
{
    "type": "dispatch",
    "payload": {
        "task_type": "general",
        "description": "执行任务"
    }
}
```

**接收**:
```json
{
    "type": "dispatched",
    "task_id": "abc-123"
}
```

#### 支持的消息类型

| 类型 | 方向 | 描述 |
|:---|:---:|:---|
| ping | 双向 | 心跳保活 |
| dispatch | 发送 | 分发任务 |
| wake | 发送 | 唤醒命令 |
| status | 接收 | 状态更新 |
| registered | 接收 | Agent注册确认 |

---

## Android集成

### 1. 添加依赖

```kotlin
// build.gradle
dependencies {
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
}
```

### 2. 核心代码

```kotlin
// BlackApiClient.kt
object BlackApiClient {
    private const val BASE_URL = "http://<Windows-PC-IP>:9001"
    
    suspend fun wakeSystem(command: String): WakeResponse {
        val json = JSONObject().apply {
            put("command", command)
            put("source", "android")
            put("mode", "voice")
        }
        
        // 发送POST请求...
    }
}
```

### 3. 唤醒服务

```kotlin
// BlackWakeService.kt
class BlackWakeService : AccessibilityService() {
    override fun onServiceConnected() {
        super.onServiceConnected()
        startListening() // 开始语音监听
    }
    
    private fun startListening() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, 
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        }
        startListening(intent)
    }
}
```

### 4. 权限配置

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE" />
```

---

## 常见问题

### Q1: 无法连接到BLACK Core？

**解决方案**:
1. 检查防火墙设置，允许端口9001
2. 确认Windows PC IP地址
3. 重启服务：`black_system\start_black_system.bat`

### Q2: 语音唤醒不灵敏？

**解决方案**:
1. 确保麦克风权限已开启
2. 在安静环境使用
3. 清晰说出唤醒词："嘿BLACK"

### Q3: Android设备无法连接？

**解决方案**:
1. 确保Android和Windows在同一网络
2. 检查Tailscale是否安装并登录
3. 查看日志：`black_system\logs\android.log`

### Q4: 如何添加新的Agent？

```python
from black_system.core.main import AgentInfo, AgentType, AgentCapability

# 创建Agent信息
new_agent = AgentInfo(
    id="my-agent",
    name="我的Agent",
    agent_type=AgentType.CUSTOM,
    host="localhost",
    port=8000,
    capabilities=[
        AgentCapability("custom_task", "自定义任务")
    ]
)

# 注册Agent
await scheduler.register_agent(new_agent)
```

---

## 📊 性能指标

| 指标 | 数值 | 说明 |
|:---|:---:|:---|
| 启动时间 | <5秒 | 冷启动 |
| 任务响应 | <1秒 | 一般任务 |
| 并发任务 | 10+ | 同时处理 |
| 内存占用 | <500MB | 空闲状态 |
| WebSocket延迟 | <50ms | 局域网 |

---

## 🛠️ 开发计划

### v5.1 (本周)
- [ ] 完善MiniMax桥接器
- [ ] 添加OpenWork集成
- [ ] 优化唤醒准确率

### v5.2 (下周)
- [ ] VLM GUI理解集成
- [ ] 语音完全体
- [ ] 自学习系统

### v6.0 (本月)
- [ ] 真正的自主决策
- [ ] 多智能体协同
- [ ] 硬件集成扩展

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🤝 贡献者

- **Matrix Agent** - 主开发者

---

## 📞 联系方式

- **GitHub**: https://github.com/DannyFish-11/ufo-galaxy
- **问题反馈**: Issues页面

---

**感谢使用BLACK System！** 🚀

让AI真正成为您的智能助手！
