"""
UFO³ Galaxy Agent Bridge
========================

功能：
集成UFO³ Galaxy系统到BLACK调度框架
提供统一的API接口调用所有UFO³ Galaxy节点

作者：Matrix Agent
版本：1.0.0
日期：2026-02-04
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class UFONodeStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class UFONode:
    """UFO³ Galaxy节点信息"""
    node_id: str
    name: str
    description: str
    category: str
    url: str
    port: int
    methods: List[str]
    status: UFONodeStatus
    priority: int = 5
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "url": self.url,
            "port": self.port,
            "methods": self.methods,
            "status": self.status.value,
            "priority": self.priority
        }


class UFOGalaxyBridge:
    """
    UFO³ Galaxy桥接器
    
    功能：
    1. 连接UFO³ Galaxy Gateway
    2. 调用所有节点功能
    3. 任务状态监控
    4. 资源管理
    """
    
    def __init__(self, gateway_url: str = "http://localhost:9000"):
        self.gateway_url = gateway_url
        self.nodes: Dict[str, UFONode] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self.connected = False
        
        # 节点分类映射
        self.category_map = {
            "00-09": "核心系统",
            "10-25": "第三方服务",
            "33-48": "设备控制",
            "50-63": "智能推理",
            "64-69": "系统管理",
            "70-74": "增强功能",
            "79-85": "v2.0功能",
            "90-99": "增强节点",
            "110-112": "智能编排",
        }
    
    async def connect(self) -> bool:
        """连接UFO³ Galaxy Gateway"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # 测试连接
            response = await self.http_client.get(f"{self.gateway_url}/health")
            if response.status_code == 200:
                self.connected = True
                print("✅ Connected to UFO³ Galaxy Gateway")
                
                # 加载节点信息
                await self._load_nodes()
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to connect to UFO³ Galaxy: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            self.connected = False
            print("🔌 Disconnected from UFO³ Galaxy")
    
    async def _load_nodes(self):
        """加载所有节点信息"""
        try:
            response = await self.http_client.get(f"{self.gateway_url}/api/node/list")
            if response.status_code == 200:
                data = response.json()
                nodes_data = data.get("nodes", [])
                
                for node_info in nodes_data:
                    node = UFONode(
                        node_id=node_info.get("node_id", ""),
                        name=node_info.get("name", ""),
                        description=node_info.get("description", ""),
                        category=node_info.get("category", ""),
                        url=node_info.get("url", ""),
                        port=node_info.get("port", 0),
                        methods=node_info.get("methods", []),
                        status=UFONodeStatus.ONLINE if node_info.get("status") == "online" else UFONodeStatus.OFFLINE,
                        priority=node_info.get("priority", 5)
                    )
                    self.nodes[node.node_id] = node
                
                print(f"📦 Loaded {len(self.nodes)} nodes from UFO³ Galaxy")
        
        except Exception as e:
            print(f"❌ Failed to load nodes: {e}")
    
    # ============ 节点操作 ============
    
    async def get_nodes(self, category: str = None, status: str = None) -> List[Dict]:
        """
        获取节点列表
        
        Args:
            category: 按分类筛选
            status: 按状态筛选
        """
        nodes = list(self.nodes.values())
        
        if category:
            nodes = [n for n in nodes if n.category == category]
        
        if status:
            status_enum = UFONodeStatus(status)
            nodes = [n for n in nodes if n.status == status_enum]
        
        return [n.to_dict() for n in nodes]
    
    async def get_node_info(self, node_id: str) -> Optional[Dict]:
        """获取单个节点信息"""
        if node_id in self.nodes:
            return self.nodes[node_id].to_dict()
        return None
    
    async def call_node(self, node_id: str, method: str, 
                       params: Dict = None) -> Dict[str, Any]:
        """
        调用节点方法
        
        Args:
            node_id: 节点ID（如 "01", "50"）
            method: 方法名
            params: 参数
            
        Returns:
            执行结果
        """
        if node_id not in self.nodes:
            return {"error": f"Node {node_id} not found"}
        
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/node/call",
                json={
                    "node_id": node_id,
                    "method": method,
                    "params": params or {}
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}", "detail": response.text}
        
        except httpx.TimeoutException:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    # ============ 核心功能 ============
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """
        执行自然语言命令
        
        通过Gateway转发到NLU引擎理解并执行
        """
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/command",
                json={"command": command},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def chat(self, messages: List[Dict[str, str]], 
                  model: str = "auto",
                  temperature: float = 0.7) -> Dict[str, Any]:
        """
        LLM对话
        
        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            model: 模型选择
            temperature: 温度参数
        """
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/llm/chat",
                json={
                    "messages": messages,
                    "model": model,
                    "temperature": temperature
                },
                timeout=120.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def simple_ask(self, question: str, 
                        system_prompt: str = None) -> str:
        """
        简单问答
        
        Args:
            question: 问题
            system_prompt: 系统提示
            
        Returns:
            回答文本
        """
        try:
            payload = {"question": question}
            if system_prompt:
                payload["system_prompt"] = system_prompt
            
            response = await self.http_client.post(
                f"{self.gateway_url}/api/llm/ask",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("answer", "")
            else:
                return f"Error: HTTP {response.status_code}"
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def code_generation(self, prompt: str, 
                             language: str = "python") -> str:
        """
        代码生成
        
        Args:
            prompt: 功能描述
            language: 编程语言
        """
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/llm/code",
                json={"prompt": prompt, "language": language},
                timeout=120.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("code", "")
            else:
                return f"Error: HTTP {response.status_code}"
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def web_search(self, query: str) -> List[Dict[str, Any]]:
        """
        网络搜索
        
        Args:
            query: 搜索关键词
        """
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/llm/search",
                json={"question": query},
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])
            else:
                return [{"error": f"HTTP {response.status_code}"}]
        
        except Exception as e:
            return [{"error": str(e)}]
    
    # ============ 设备控制 ============
    
    async def android_control(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Android设备控制
        
        Args:
            action: 操作类型
                - launch_app: 启动应用
                - click: 点击坐标
                - swipe: 滑动
                - input_text: 输入文本
                - get_screen: 获取屏幕
            **kwargs: 其他参数
        """
        result = await self.call_node(
            node_id="33",  # ADB节点
            method=action,
            params=kwargs
        )
        return result
    
    async def windows_control(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Windows系统控制
        
        Args:
            action: 操作类型
                - click: 点击
                - type: 输入文本
                - hotkey: 快捷键
                - window: 窗口操作
            **kwargs: 其他参数
        """
        result = await self.call_node(
            node_id="36",  # UIAWindows节点
            method=action,
            params=kwargs
        )
        return result
    
    async def automation(self, task: str) -> Dict[str, Any]:
        """
        自动化任务执行
        
        Args:
            task: 任务描述
        """
        # 通过NLU理解任务并自动编排
        return await self.execute_command(task)
    
    # ============ 系统管理 ============
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        try:
            response = await self.http_client.get(f"{self.gateway_url}/api/stats")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        try:
            response = await self.http_client.get(f"{self.gateway_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                
                # 获取节点状态
                nodes = await self.get_nodes()
                online_count = sum(1 for n in nodes if n.get("status") == "online")
                
                return {
                    "status": "healthy",
                    "gateway": "online",
                    "nodes_total": len(nodes),
                    "nodes_online": online_count,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"status": "unhealthy", "error": "Gateway not responding"}
        
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    # ============ 批量操作 ============
    
    async def batch_execute(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表 [{"node": "01", "method": "chat", "params": {...}}]
        """
        results = []
        
        for task in tasks:
            try:
                result = await self.call_node(
                    node_id=task.get("node", ""),
                    method=task.get("method", ""),
                    params=task.get("params", {})
                )
                
                results.append({
                    "node": task.get("node"),
                    "method": task.get("method"),
                    "status": "success",
                    "result": result
                })
            
            except Exception as e:
                results.append({
                    "node": task.get("node"),
                    "method": task.get("method"),
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def execute_parallel(self, commands: List[str]) -> List[Dict[str, Any]]:
        """
        并行执行多个命令
        
        Args:
            commands: 命令列表
        """
        tasks = [self.execute_command(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                output.append({
                    "command": commands[i],
                    "status": "error",
                    "error": str(result)
                })
            else:
                output.append({
                    "command": commands[i],
                    "status": "success",
                    "result": result
                })
        
        return output


# ============ 便捷函数 ============

async def create_bridge(gateway_url: str = "http://localhost:9000") -> UFOGalaxyBridge:
    """创建并连接桥接器"""
    bridge = UFOGalaxyBridge(gateway_url)
    connected = await bridge.connect()
    
    if connected:
        return bridge
    else:
        raise ConnectionError(f"Failed to connect to UFO³ Galaxy at {gateway_url}")


# ============ 使用示例 ============

async def example():
    """使用示例"""
    bridge = await create_bridge()
    
    # 获取系统状态
    overview = await bridge.get_system_overview()
    print(f"Nodes: {overview.get('total_nodes', 0)}")
    
    # 执行命令
    result = await bridge.execute_command("搜索今天的新闻")
    print(result)
    
    # LLM对话
    response = await bridge.chat([
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ])
    print(response)
    
    # 断开连接
    await bridge.disconnect()


if __name__ == "__main__":
    asyncio.run(example())
