"""
BLACK System Core - 统一智能体调度核心
=====================================

功能：
1. 统一管理所有本地Agent（MiniMax、UFO³ Galaxy、OpenWork等）
2. 智能任务分发和调度
3. 冲突检测与解决
4. 跨设备唤醒和协同
5. 资源共享管理

作者：Matrix Agent
版本：5.0.0
日期：2026-02-04
"""

import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn


# ============ 常量定义 ============

BLACK_CORE_PORT = 9001
DEFAULT_TIMEOUT = 30.0

# Agent类型枚举
class AgentType(Enum):
    MINIMAX = "minimax"
    UFO_GALAXY = "ufo_galaxy"
    OPENWORK = "openwork"
    CUSTOM = "custom"
    WINDOWS = "windows"
    ANDROID = "android"
    CLOUD = "cloud"

# 任务优先级
class TaskPriority(Enum):
    CRITICAL = 1  # 系统关键任务
    HIGH = 3      # 高优先级
    MEDIUM = 5    # 中等优先级（默认）
    LOW = 7       # 低优先级
    BACKGROUND = 9 # 后台任务

# ============ 数据模型 ============

@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)

@dataclass
class AgentInfo:
    """Agent信息"""
    id: str
    name: str
    agent_type: AgentType
    host: str
    port: int
    status: str = "offline"
    capabilities: List[AgentCapability] = field(default_factory=list)
    last_heartbeat: Optional[datetime] = None
    load: float = 0.0  # 当前负载 0-1
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "capabilities": [cap.__dict__ for cap in self.capabilities],
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "load": self.load,
            "version": self.version
        }

class TaskRequest(BaseModel):
    """任务请求"""
    task_type: str = Field(..., description="任务类型")
    description: str = Field(..., description="任务描述")
    priority: TaskPriority = TaskPriority.MEDIUM
    source: str = Field("unknown", description="唤醒源")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    require_capabilities: List[str] = Field(default_factory=list)
    timeout: float = DEFAULT_TIMEOUT
    
class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    status: str  # pending, running, completed, failed, timeout
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    executor: Optional[str] = None
    timestamp: str = ""

class WakeCommand(BaseModel):
    """唤醒命令"""
    command: str = Field(..., description="唤醒命令文本")
    source: str = Field("unknown", description="唤醒源设备/节点")
    mode: str = Field("auto", description="唤醒模式: auto, voice, text, gesture")
    context: Dict[str, Any] = Field(default_factory=dict)

# ============ 统一调度器 ============

class UnifiedScheduler:
    """
    统一任务调度器
    
    核心功能：
    1. Agent注册与管理
    2. 智能任务分发
    3. 负载均衡
    4. 冲突检测
    5. 任务追踪
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.tasks: Dict[str, TaskResult] = {}
        self.task_history: List[Dict] = []
        self.running = False
        
        # 任务队列（优先级队列）
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # 负载均衡器
        self.load_weights: Dict[str, float] = {
            "capability_match": 0.4,  # 能力匹配权重
            "load_factor": 0.3,         # 当前负载权重
            "priority_factor": 0.2,    # 任务优先级权重
            "latency_factor": 0.1      # 延迟权重
        }
        
        # 冲突检测器
        self.locked_resources: Dict[str, Set[str]] = {}
        self.executing_tasks: Dict[str, str] = {}  # task_id -> agent_id
    
    async def start(self):
        """启动调度器"""
        self.running = True
        
        # 启动后台任务处理器
        asyncio.create_task(self._task_processor())
        
        # 启动心跳检测
        asyncio.create_task(self._heartbeat_monitor())
        
        print(f"🟢 BLACK Scheduler started on port {BLACK_CORE_PORT}")
        print(f"   Agents registered: {len(self.agents)}")
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        print("🔴 BLACK Scheduler stopped")
    
    # ============ Agent管理 ============
    
    async def register_agent(self, agent: AgentInfo) -> bool:
        """注册Agent"""
        self.agents[agent.id] = agent
        
        # 设置默认能力
        if not agent.capabilities:
            agent.capabilities = self._get_default_capabilities(agent.agent_type)
        
        print(f"✅ Agent registered: {agent.name} ({agent.agent_type.value})")
        print(f"   Capabilities: {[c.name for c in agent.capabilities]}")
        
        return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """注销Agent"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            print(f"❌ Agent unregistered: {agent.name}")
            return True
        return False
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Agent心跳"""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now()
            return True
        return False
    
    def _get_default_capabilities(self, agent_type: AgentType) -> List[AgentCapability]:
        """获取默认能力列表"""
        capability_map = {
            AgentType.UFO_GALAXY: [
                AgentCapability("general_task", "执行一般任务", {"type": "string"}),
                AgentCapability("web_search", "网络搜索"),
                AgentCapability("code_generation", "代码生成", {"language": "string"}),
                AgentCapability("automation", "自动化控制"),
                AgentCapability("file_operation", "文件操作"),
                AgentCapability("llm", "大语言模型对话"),
            ],
            AgentType.MINIMAX: [
                AgentCapability("chat", "对话交流"),
                AgentCapability("image_gen", "图像生成"),
                AgentCapability("code", "代码相关"),
            ],
            AgentType.ANDROID: [
                AgentCapability("android_control", "Android设备控制"),
                AgentCapability("app_launch", "应用启动"),
                AgentCapability("gesture", "手势操作"),
                AgentCapability("voice_input", "语音输入"),
            ],
            AgentType.WINDOWS: [
                AgentCapability("windows_control", "Windows系统控制"),
                AgentCapability("ui_automation", "UI自动化"),
                AgentCapability("process", "进程管理"),
            ],
            AgentType.CLOUD: [
                AgentCapability("cloud_compute", "云端计算"),
                AgentCapability("storage", "云存储"),
            ]
        }
        return capability_map.get(agent_type, [
            AgentCapability("general", "通用能力")
        ])
    
    # ============ 任务分发 ============
    
    async def dispatch(self, request: TaskRequest) -> str:
        """
        分发任务到最佳Agent
        
        流程：
        1. 分析任务需求
        2. 筛选可用Agent
        3. 计算评分
        4. 选择最佳Agent
        5. 执行任务
        """
        task_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # 创建任务记录
        self.tasks[task_id] = TaskResult(
            task_id=task_id,
            status="pending",
            result=None,
            duration=0.0,
            timestamp=timestamp
        )
        
        print(f"📝 Task queued: {task_id} - {request.description[:50]}...")
        
        # 添加到优先级队列
        await self.task_queue.put((request.priority.value, task_id, request))
        
        return task_id
    
    async def _task_processor(self):
        """后台任务处理器"""
        while self.running:
            try:
                # 从队列获取任务
                _, task_id, request = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # 执行任务
                asyncio.create_task(self._execute_task(task_id, request))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Task processor error: {e}")
    
    async def _execute_task(self, task_id: str, request: TaskRequest):
        """执行单个任务"""
        start_time = datetime.now()
        
        self.tasks[task_id].status = "running"
        
        # 1. 分析任务需求
        required_capabilities = self._analyze_task(request)
        
        # 2. 选择最佳Agent
        best_agent = await self._select_agent(required_capabilities, request.priority)
        
        if not best_agent:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = "No available agent"
            print(f"❌ Task {task_id} failed: No agent available")
            return
        
        # 3. 检查并获取资源锁
        resources = self._get_required_resources(request)
        if not await self._acquire_resources(task_id, resources, best_agent.id):
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = "Resource conflict"
            print(f"❌ Task {task_id} failed: Resource conflict")
            return
        
        self.tasks[task_id].executor = best_agent.id
        self.executing_tasks[task_id] = best_agent.id
        
        print(f"🚀 Task {task_id} executing on {best_agent.name}")
        
        try:
            # 4. 执行任务（调用Agent API）
            result = await self._call_agent(best_agent, request)
            
            self.tasks[task_id].status = "completed"
            self.tasks[task_id].result = result
            
            print(f"✅ Task {task_id} completed")
            
        except Exception as e:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = str(e)
            print(f"❌ Task {task_id} failed: {e}")
        
        finally:
            # 5. 释放资源锁
            await self._release_resources(task_id, resources)
            
            # 6. 记录到历史
            duration = (datetime.now() - start_time).total_seconds()
            self.tasks[task_id].duration = duration
            
            self.task_history.append({
                "task_id": task_id,
                "agent": best_agent.name,
                "type": request.task_type,
                "description": request.description,
                "duration": duration,
                "status": self.tasks[task_id].status,
                "timestamp": self.tasks[task_id].timestamp
            })
            
            # 清理已完成任务
            self.executing_tasks.pop(task_id, None)
    
    def _analyze_task(self, request: TaskRequest) -> List[str]:
        """
        分析任务需求，提取所需能力
        
        简单规则匹配，后续可接入NLU引擎
        """
        text = request.description.lower()
        required = request.require_capabilities.copy()
        
        # 关键词匹配
        keyword_map = {
            "search": ["搜索", "查找", "search", "find"],
            "code": ["代码", "编程", "code", "programming"],
            "automation": ["自动化", "控制", "automation", "control"],
            "file": ["文件", "folder", "文件操作"],
            "chat": ["对话", "聊天", "chat", "talk"],
            "android": ["安卓", "android", "手机"],
            "windows": ["windows", "系统", "system"],
            "web": ["网页", "web", "浏览器"],
            "image": ["图片", "图像", "image", "生成图片"],
            "video": ["视频", "video"],
            "music": ["音乐", "music"],
            "translate": ["翻译", "translate"],
            "weather": ["天气", "weather"],
            "news": ["新闻", "news"],
        }
        
        for capability, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                if capability not in required:
                    required.append(capability)
        
        # 默认添加通用能力
        if "general" not in required:
            required.append("general")
        
        return required
    
    async def _select_agent(self, required_capabilities: List[str], 
                           priority: TaskPriority) -> Optional[AgentInfo]:
        """
        选择最佳Agent（负载均衡+能力匹配）
        """
        available_agents = [
            agent for agent in self.agents.values()
            if agent.status == "online"
            and agent.load < 0.9  # 负载小于90%
        ]
        
        if not available_agents:
            return None
        
        # 计算每个Agent的评分
        scores = []
        for agent in available_agents:
            score = self._calculate_agent_score(agent, required_capabilities, priority)
            scores.append((score, agent))
        
        # 选择最高分
        scores.sort(key=lambda x: x[0], reverse=True)
        
        if scores:
            # 更新选中Agent的负载
            selected = scores[0][1]
            selected.load = min(selected.load + 0.1, 1.0)
            return selected
        
        return None
    
    def _calculate_agent_score(self, agent: AgentInfo, 
                              required: List[str], 
                              priority: TaskPriority) -> float:
        """计算Agent评分"""
        score = 0.0
        
        # 1. 能力匹配度 (0-40分)
        agent_caps = [c.name for c in agent.capabilities]
        match_count = sum(1 for cap in required if cap in agent_caps)
        capability_score = (match_count / len(required)) * 40 if required else 20
        score += capability_score
        
        # 2. 负载评分 (0-30分)
        load_score = (1 - agent.load) * 30
        score += load_score
        
        # 3. 优先级考虑 (0-20分)
        priority_bonus = {
            TaskPriority.CRITICAL: 20,
            TaskPriority.HIGH: 15,
            TaskPriority.MEDIUM: 10,
            TaskPriority.LOW: 5,
            TaskPriority.BACKGROUND: 0
        }
        score += priority_bonus.get(priority, 10)
        
        # 4. 随机因素（防止饥饿）(0-10分)
        import random
        score += random.uniform(0, 10)
        
        return score
    
    def _get_required_resources(self, request: TaskRequest) -> Set[str]:
        """获取任务需要的资源"""
        resources = set()
        
        task_type = request.task_type.lower()
        
        if "automation" in task_type:
            resources.add("keyboard")
            resources.add("mouse")
        if "file" in task_type:
            resources.add("filesystem")
        if "network" in task_type:
            resources.add("network")
        if "android" in task_type:
            resources.add("adb")
        
        return resources
    
    async def _acquire_resources(self, task_id: str, resources: Set[str], 
                                 agent_id: str) -> bool:
        """获取资源锁"""
        for resource in resources:
            # 检查是否被锁定
            if resource in self.locked_resources:
                locked_by = self.locked_resources[resource]
                if locked_by != task_id and locked_by in self.executing_tasks:
                    return False  # 资源被其他任务占用
        
        # 获取所有资源锁
        for resource in resources:
            self.locked_resources[resource] = task_id
        
        return True
    
    async def _release_resources(self, task_id: str, resources: Set[str]):
        """释放资源锁"""
        for resource in resources:
            if resource in self.locked_resources and self.locked_resources[resource] == task_id:
                del self.locked_resources[resource]
    
    async def _call_agent(self, agent: AgentInfo, request: TaskRequest) -> Any:
        """
        调用Agent执行任务
        
        这里应该根据Agent类型调用不同的API
        简化版：直接返回成功响应
        """
        # 模拟执行
        await asyncio.sleep(0.5)
        
        # 根据Agent类型调用不同接口
        if agent.agent_type == AgentType.UFO_GALAXY:
            # 调用UFO³ Galaxy Gateway
            return await self._call_ufo_galaxy(request)
        elif agent.agent_type == AgentType.MINIMAX:
            # 调用MiniMax
            return await self._call_minimax(request)
        elif agent.agent_type == AgentType.ANDROID:
            # 调用Android Agent
            return await self._call_android(request)
        else:
            return {"message": f"Task executed by {agent.name}"}
    
    async def _call_ufo_galaxy(self, request: TaskRequest) -> Dict:
        """调用UFO³ Galaxy"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:9000/api/command",
                    json={"command": request.description},
                    timeout=request.timeout
                )
                return response.json()
        except Exception as e:
            return {"error": str(e), "source": "ufo_galaxy"}
    
    async def _call_minimax(self, request: TaskRequest) -> Dict:
        """调用MiniMax"""
        # TODO: 实现MiniMax API调用
        return {"message": "MiniMax task executed", "type": request.task_type}
    
    async def _call_android(self, request: TaskRequest) -> Dict:
        """调用Android Agent"""
        # TODO: 实现Android API调用
        return {"message": "Android task executed", "type": request.task_type}
    
    # ============ 心跳监控 ============
    
    async def _heartbeat_monitor(self):
        """心跳监控（每10秒检查一次）"""
        while self.running:
            await asyncio.sleep(10)
            
            now = datetime.now()
            timeout = 30  # 30秒超时
            
            for agent_id, agent in self.agents.items():
                if agent.last_heartbeat:
                    elapsed = (now - agent.last_heartbeat).total_seconds()
                    if elapsed > timeout:
                        # Agent离线
                        agent.status = "offline"
                        print(f"⚠️ Agent {agent.name} is offline")
    
    # ============ 状态查询 ============
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        online = sum(1 for a in self.agents.values() if a.status == "online")
        
        return {
            "running": self.running,
            "agents_total": len(self.agents),
            "agents_online": online,
            "agents_offline": len(self.agents) - online,
            "tasks_pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "tasks_running": sum(1 for t in self.tasks.values() if t.status == "running"),
            "tasks_completed": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "tasks_failed": sum(1 for t in self.tasks.values() if t.status == "failed"),
        }
    
    def get_agents(self) -> List[Dict]:
        """获取所有Agent信息"""
        return [agent.to_dict() for agent in self.agents.values()]
    
    def get_tasks(self, limit: int = 20) -> List[Dict]:
        """获取任务列表"""
        tasks = list(self.tasks.values())[-limit:]
        return [t.dict() for t in tasks]
    
    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        if task_id in self.tasks:
            return self.tasks[task_id].dict()
        return None


# ============ FastAPI应用 ============

app = FastAPI(
    title="BLACK System Core",
    description="统一智能体调度核心 - Unified Agent Scheduling Core",
    version="5.0.0"
)

# 初始化调度器
scheduler = UnifiedScheduler()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    await scheduler.start()
    
    # 自动注册内置Agent
    built_in_agents = [
        AgentInfo(
            id="ufo-galaxy-main",
            name="UFO³ Galaxy Core",
            agent_type=AgentType.UFO_GALAXY,
            host="localhost",
            port=9000,
            status="online"
        ),
        AgentInfo(
            id="windows-control",
            name="Windows Controller",
            agent_type=AgentType.WINDOWS,
            host="localhost",
            port=0,  # 本地
            status="online",
            capabilities=[
                AgentCapability("windows_control", "Windows系统控制"),
                AgentCapability("ui_automation", "UI自动化"),
            ]
        ),
        AgentInfo(
            id="android-bridge",
            name="Android Bridge",
            agent_type=AgentType.ANDROID,
            host="localhost",
            port=0,
            status="online",
            capabilities=[
                AgentCapability("android_control", "Android设备控制"),
                AgentCapability("voice_input", "语音输入"),
            ]
        ),
    ]
    
    for agent in built_in_agents:
        await scheduler.register_agent(agent)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    await scheduler.stop()


# ============ API端点 ============

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "BLACK System Core",
        "version": "5.0.0",
        "status": "running" if scheduler.running else "stopped",
        "port": BLACK_CORE_PORT,
        "endpoints": {
            "status": "/api/status",
            "agents": "/api/agents",
            "tasks": "/api/tasks",
            "dispatch": "/api/task/dispatch",
            "wake": "/api/wake",
            "websocket": "/ws"
        }
    }


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    return scheduler.get_status()


@app.get("/api/agents")
async def list_agents():
    """获取所有Agent"""
    return {
        "count": len(scheduler.agents),
        "agents": scheduler.get_agents()
    }


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """获取单个Agent信息"""
    if agent_id in scheduler.agents:
        return scheduler.agents[agent_id].to_dict()
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/api/agent/register")
async def register_agent(agent: AgentInfo):
    """注册新Agent"""
    await scheduler.register_agent(agent)
    return {"status": "registered", "agent_id": agent.id}


@app.post("/api/agent/unregister/{agent_id}")
async def unregister_agent(agent_id: str):
    """注销Agent"""
    success = await scheduler.unregister_agent(agent_id)
    if success:
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="Agent not found")


@app.post("/api/agent/heartbeat/{agent_id}")
async def agent_heartbeat(agent_id: str):
    """Agent心跳"""
    if await scheduler.heartbeat(agent_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Agent not found")


@app.get("/api/tasks")
async def list_tasks(limit: int = 20):
    """获取任务列表"""
    return {
        "count": len(scheduler.tasks),
        "tasks": scheduler.get_tasks(limit)
    }


@app.get("/api/tasks/{task_id}")
async def get_task_result(task_id: str):
    """获取任务结果"""
    result = scheduler.get_task_result(task_id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/task/dispatch")
async def dispatch_task(request: TaskRequest):
    """
    分发任务
    
    请求体：
    {
        "task_type": "automation",
        "description": "打开微信并发送消息",
        "priority": "MEDIUM",
        "source": "voice",
        "parameters": {},
        "require_capabilities": ["android_control", "automation"]
    }
    """
    try:
        task_id = await scheduler.dispatch(request)
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Task queued successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wake")
async def wake_system(command: WakeCommand):
    """
    唤醒系统执行命令
    
    请求体：
    {
        "command": "帮我打开微信并发送消息给张三",
        "source": "android",
        "mode": "voice",
        "context": {}
    }
    """
    # 创建任务请求
    task_request = TaskRequest(
        task_type="general",
        description=command.command,
        priority=TaskPriority.HIGH,
        source=command.source,
        parameters=command.context
    )
    
    # 分发任务
    task_id = await scheduler.dispatch(task_request)
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": f"Command received from {command.source}",
        "command": command.command
    }


@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    """
    WebSocket实时通信
    
    支持：
    1. 实时任务状态推送
    2. 唤醒命令推送
    3. Agent状态监控
    """
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 处理不同类型消息
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "dispatch":
                # 任务分发
                request = TaskRequest(**data.get("payload", {}))
                task_id = await scheduler.dispatch(request)
                await websocket.send_json({
                    "type": "dispatched",
                    "task_id": task_id
                })
            
            elif msg_type == "wake":
                # 唤醒命令
                command = WakeCommand(**data.get("payload", {}))
                task_request = TaskRequest(
                    task_type="general",
                    description=command.command,
                    priority=TaskPriority.HIGH,
                    source=command.source
                )
                task_id = await scheduler.dispatch(task_request)
                await websocket.send_json({
                    "type": "waking",
                    "task_id": task_id,
                    "command": command.command
                })
            
            elif msg_type == "status":
                # 状态查询
                await websocket.send_json({
                    "type": "status",
                    "data": scheduler.get_status()
                })
            
            elif msg_type == "register":
                # Agent注册
                agent_info = AgentInfo(**data.get("payload", {}))
                await scheduler.register_agent(agent_info)
                await websocket.send_json({
                    "type": "registered",
                    "agent_id": agent_info.id
                })
    
    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")


# ============ 挂载静态文件 ============

# 创建UI目录（如果不存在）
ui_dir = Path(__file__).parent.parent / "ui"
if not ui_dir.exists():
    ui_dir.mkdir(parents=True)

# 挂载Dashboard
dashboard_dir = Path(__file__).parent.parent.parent / "dashboard" / "frontend"
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir)), name="dashboard")


# ============ 启动服务 ============

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🚀 BLACK System Core v5.0.0                            ║
    ║   统一智能体调度核心                                       ║
    ║                                                           ║
    ║   端口: 9001                                              ║
    ║   WebSocket: ws://localhost:9001/ws                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=BLACK_CORE_PORT,
        log_level="info"
    )
