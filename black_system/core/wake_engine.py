"""
BLACK Wake Engine - 跨节点唤醒引擎
==================================

功能：
1. 多模态唤醒（语音、文本、快捷键、手势）
2. 自然语言理解
3. 意图识别与任务分发
4. 跨设备协同

作者：Matrix Agent
版本：1.0.0
日期：2026-02-04
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class WakeMode(Enum):
    VOICE = "voice"
    TEXT = "text"
    GESTURE = "gesture"
    HOTKEY = "hotkey"
    AUTO = "auto"


class IntentType(Enum):
    GENERAL = "general"
    SEARCH = "search"
    CONTROL = "control"
    CHAT = "chat"
    CODE = "code"
    FILE = "file"
    AUTOMATION = "automation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class WakeContext:
    """唤醒上下文"""
    mode: WakeMode
    source: str  # 唤醒源设备/节点
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    raw_command: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "raw_command": self.raw_command
        }


@dataclass
class Intent:
    """识别到的意图"""
    type: IntentType
    action: str
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    nlu_result: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "nl_result": self.nlu_result
        }


class WakeEngine:
    """
    跨节点唤醒引擎
    
    功能：
    1. 接收多模态唤醒信号
    2. 自然语言理解
    3. 意图识别与槽位填充
    4. 任务生成与分发
    5. 响应生成
    """
    
    def __init__(self):
        # 意图识别规则
        self.intent_patterns: Dict[IntentType, List[Dict]] = {
            IntentType.SEARCH: [
                {"pattern": r"(搜索|查找|找|look for|search).*", "action": "web_search"},
                {"pattern": r"(今天的|最近|latest).*(新闻|news)", "action": "news_search"},
                {"pattern": r"(天气|weather)", "action": "weather_query"},
            ],
            IntentType.CONTROL: [
                {"pattern": r"(打开|启动|launch|open).*(应用|app|程序)?", "action": "open_app"},
                {"pattern": r"(关闭|退出|close|quit).*(应用|app|程序)?", "action": "close_app"},
                {"pattern": r"(截图|screenshot|capture).*", "action": "take_screenshot"},
                {"pattern": r"(音量|volume).*(大|小|高|低|up|down)?", "action": "adjust_volume"},
            ],
            IntentType.AUTOMATION: [
                {"pattern": r"(自动化|auto|automatic).*", "action": "run_automation"},
                {"pattern": r"(帮我|帮我做|help me).*", "action": "assist_task"},
                {"pattern": r"(点击|tap|click).*", "action": "perform_click"},
                {"pattern": r"(滑动|swipe|滑动).*", "action": "perform_swipe"},
            ],
            IntentType.CHAT: [
                {"pattern": r"(你好|hello|hi|在吗|are you there)", "action": "greeting"},
                {"pattern": r"(聊聊|聊天|talk).*", "action": "start_chat"},
                {"pattern": r"(解释|explain|什么是|what is).*", "action": "explain"},
            ],
            IntentType.CODE: [
                {"pattern": r"(写代码|生成代码|code|编程).*", "action": "generate_code"},
                {"pattern": r"(debug|调试|修复|fix).*", "action": "debug_code"},
                {"pattern": r"(解释代码|explain code).*", "action": "explain_code"},
            ],
            IntentType.FILE: [
                {"pattern": r"(创建|新建|create).*(文件|folder|目录)?", "action": "create_file"},
                {"pattern": r"(打开|open).*(文件|file|文档)?", "action": "open_file"},
                {"pattern": r"(删除|delete|remove).*(文件|file)?", "action": "delete_file"},
                {"pattern": r"(搜索|找|find).*(文件|file)?", "action": "search_file"},
            ],
            IntentType.SYSTEM: [
                {"pattern": r"(关机|shutdown|关机|turn off).*", "action": "shutdown"},
                {"pattern": r"(重启|restart|reboot).*", "action": "restart"},
                {"pattern": r"(设置|setting|config).*", "action": "open_settings"},
                {"pattern": r"(帮助|help|使用说明).*", "action": "show_help"},
            ]
        }
        
        # 实体提取模式
        self.entity_patterns = {
            "app": r"(微信|wechat|qq|浏览器|browser|chrome|edge|文件管理器|explorer|vscode|code)",
            "number": r"\d+(\.\d+)?",
            "filepath": r"[a-zA-Z]:\\[\\\S| ]+|(?<=)(/[\w/ ]+)+",
            "time": r"(\d{1,2}:\d{2}|今天|明天|后天|明天|昨天)",
            "person": r"(张三|李四|王五|小明|小红|用户|我|你)",
        }
        
        # 回调函数
        self.on_wake: Optional[Callable] = None
        self.on_intent: Optional[Callable] = None
        self.on_response: Optional[Callable] = None
        
        # 唤醒词
        self.wake_words = ["black", "布莱克", "嘿black", "喂black", "小黑"]
        
        # 上下文历史
        self.context_history: List[WakeContext] = []
        self.max_history = 10
    
    def set_callbacks(self, 
on_wake: Callable[[WakeContext], Any] = None,
                    on_intent: Callable[[WakeContext, Intent], Any] = None,
                    on_response: Callable[[WakeContext, Intent, Any], Any] = None):
        """
        设置回调函数
        
        Args:
            on_wake: 唤醒回调
            on_intent: 意图识别回调
            on_response: 响应生成回调
        """
        self.on_wake = on_wake
        self.on_intent = on_intent
        self.on_response = on_response
    
    # ============ 唤醒处理 ============
    
    async def process_wake(self, command: str, 
                          mode: WakeMode = WakeMode.AUTO,
                          source: str = "unknown",
                          **kwargs) -> Dict[str, Any]:
        """
        处理唤醒命令
        
        Args:
            command: 原始命令
            mode: 唤醒模式
            source: 唤醒源
            
        Returns:
            处理结果
        """
        # 创建上下文
        context = WakeContext(
            mode=mode,
            source=source,
            raw_command=command,
            **kwargs
        )
        
        # 保存到历史
        self.context_history.append(context)
        if len(self.context_history) > self.max_history:
            self.context_history.pop(0)
        
        # 触发唤醒回调
        if self.on_wake:
            await self.on_wake(context)
        
        print(f"🎯 Wake received: {command} (from {source})")
        
        # 1. 检测唤醒词
        has_wake_word = self._detect_wake_word(command)
        if has_wake_word:
            command = command.replace(has_wake_word, "").strip()
        
        # 2. 自然语言理解
        nlu_result = self._nlu_process(command)
        
        # 3. 意图识别
        intent = self._recognize_intent(command, nlu_result)
        intent.nlu_result = nlu_result
        
        # 触发意图回调
        if self.on_intent:
            result = await self.on_intent(context, intent)
            if result is not None:
                return {
                    "success": True,
                    "context": context.to_dict(),
                    "intent": intent.to_dict(),
                    "result": result
                }
        
        # 4. 生成任务描述
        task_description = self._generate_task_description(intent, command)
        
        # 5. 返回处理结果
        response = {
            "success": True,
            "has_wake_word": bool(has_wake_word),
            "context": context.to_dict(),
            "intent": intent.to_dict(),
            "task_description": task_description,
            "nlu_result": nlu_result
        }
        
        # 触发响应回调
        if self.on_response:
            response_data = await self.on_response(context, intent, task_description)
            response["response"] = response_data
        
        return response
    
    def _detect_wake_word(self, command: str) -> Optional[str]:
        """检测唤醒词"""
        command_lower = command.lower()
        
        for wake_word in self.wake_words:
            if wake_word.lower() in command_lower:
                return wake_word
        
        return None
    
    def _nlu_process(self, command: str) -> Dict[str, Any]:
        """
        自然语言处理
        
        提取：
        1. 关键实体
        2. 情感倾向
        3. 句式结构
        """
        entities = {}
        
        # 提取实体
        for entity_name, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, command, re.IGNORECASE)
            if matches:
                entities[entity_name] = matches[0] if len(matches) == 1 else matches
        
        # 基本分析
        analysis = {
            "text": command,
            "length": len(command),
            "word_count": len(command.split()),
            "has_question": "?" in command or "？" in command or any(
                kw in command for kw in ["吗", "呢", "什么", "how", "what", "where"]
            ),
            "has_please": any(
                kw in command for kw in ["请", "帮我", "帮我", "please", "帮"]
            ),
            "urgency": self._detect_urgency(command),
            "entities": entities
        }
        
        return analysis
    
    def _detect_urgency(self, command: str) -> str:
        """检测紧急程度"""
        urgent_words = ["紧急", "马上", "立即", "立刻", "urgent", "asap", "now"]
        polite_words = ["不急", "慢慢", "later", "sometime"]
        
        if any(word in command for word in urgent_words):
            return "high"
        elif any(word in command for word in polite_words):
            return "low"
        return "normal"
    
    def _recognize_intent(self, command: str, nlu_result: Dict) -> Intent:
        """
        意图识别
        
        使用规则+模式匹配进行意图识别
        后续可接入LLM进行增强
        """
        best_intent = Intent(
            type=IntentType.GENERAL,
            action="general_task",
            target="general",
            confidence=0.5
        )
        
        best_score = 0
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                action = pattern_info["action"]
                
                # 模式匹配
                if re.search(pattern, command, re.IGNORECASE):
                    # 计算置信度
                    match = re.search(pattern, command, re.IGNORECASE)
                    match_length = match.end() - match.start()
                    confidence = min(match_length / len(command) + 0.3, 0.95)
                    
                    if confidence > best_score:
                        best_score = confidence
                        best_intent = Intent(
                            type=intent_type,
                            action=action,
                            target=self._extract_target(command, intent_type),
                            parameters=self._extract_parameters(command, intent_type, nlu_result),
                            confidence=confidence
                        )
        
        # 如果所有置信度都很低，设置为UNKNOWN
        if best_score < 0.3:
            best_intent.type = IntentType.UNKNOWN
            best_intent.action = "handle_unknown"
        
        return best_intent
    
    def _extract_target(self, command: str, intent_type: IntentType) -> str:
        """提取目标"""
        targets = {
            IntentType.SEARCH: "web",
            IntentType.CONTROL: "system",
            IntentType.AUTOMATION: "automation",
            IntentType.CHAT: "conversation",
            IntentType.CODE: "development",
            IntentType.FILE: "filesystem",
            IntentType.SYSTEM: "os"
        }
        return targets.get(intent_type, "general")
    
    def _extract_parameters(self, command: str, intent_type: IntentType, 
                           nlu_result: Dict) -> Dict[str, Any]:
        """提取参数"""
        params = {}
        
        # 从实体中提取参数
        entities = nlu_result.get("entities", {})
        
        if "app" in entities:
            params["app_name"] = entities["app"]
        
        if "number" in entities:
            params["value"] = int(entities["number"])
        
        if "filepath" in entities:
            params["path"] = entities["filepath"]
        
        if "person" in entities:
            params["target_person"] = entities["person"]
        
        # 特殊处理
        if intent_type == IntentType.CONTROL and "打开" in command or "open" in command.lower():
            if "app_name" not in params:
                # 尝试提取应用名
                app_match = re.search(r"(打开|启动|open)\s+(\S+)", command)
                if app_match:
                    params["app_name"] = app_match.group(2)
        
        return params
    
    def _generate_task_description(self, intent: Intent, original_command: str) -> str:
        """
        生成任务描述
        
        将自然语言转换为结构化任务描述
        """
        desc_parts = [f"执行{intents.action}任务"]
        
        if intent.target != "general":
            desc_parts.append(f"目标: {intent.target}")
        
        if intent.parameters:
            params_str = ", ".join([f"{k}={v}" for k, v in intent.parameters.items()])
            desc_parts.append(f"参数: {params_str}")
        
        return " | ".join(desc_parts)
    
    # ============ 快捷命令 ============
    
    def register_shortcut(self, shortcut: str, command: str):
        """
        注册快捷命令
        
        例如：
        shortcut: "关机"
        command: "执行系统关机操作"
        """
        self.intent_patterns[IntentType.SYSTEM].append({
            "pattern": shortcut,
            "action": command
        })
        print(f"✅ Shortcut registered: {shortcut} -> {command}")
    
    # ============ 上下文管理 ============
    
    def get_last_context(self) -> Optional[WakeContext]:
        """获取上一个上下文"""
        if self.context_history:
            return self.context_history[-1]
        return None
    
    def get_context_history(self, limit: int = 10) -> List[Dict]:
        """获取上下文历史"""
        return [ctx.to_dict() for ctx in self.context_history[-limit:]]
    
    def clear_history(self):
        """清空历史"""
        self.context_history.clear()
        print("🗑️ Context history cleared")
    
    # ============ 批处理 ============
    
    async def process_batch(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理唤醒命令
        
        Args:
            commands: 命令列表 [{"command": "...", "source": "android"}]
        """
        tasks = [
            self.process_wake(
                cmd["command"],
                mode=WakeMode(cmd.get("mode", "auto")),
                source=cmd.get("source", "unknown")
            )
            for cmd in commands
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                output.append({
                    "command": commands[i]["command"],
                    "success": False,
                    "error": str(result)
                })
            else:
                output.append(result)
        
        return output


# ============ 与LLM集成 ============

class NLUWithLLM:
    """
    基于LLM的自然语言理解
    
    使用UFO³ Galaxy的NLU引擎进行更准确的意图识别
    """
    
    def __init__(self, bridge):
        """
        初始化
        
        Args:
            bridge: UFO³ Galaxy桥接器实例
        """
        self.bridge = bridge
    
    async def understand(self, text: str) -> Dict[str, Any]:
        """
        理解自然语言
        
        使用LLM提取：
        1. 意图类型
        2. 执行动作
        3. 相关实体
        4. 置信度
        """
        prompt = f"""
请分析以下自然语言命令，提取关键信息：

命令：{text}

请以JSON格式返回：
{{
    "intent": "意图类型（search/control/chat/code/file/automation/system/general）",
    "action": "具体动作",
    "target": "操作目标",
    "entities": {{"实体名": "实体值", ...}},
    "confidence": 0.0-1.0,
    "suggested_response": "建议的回复"
}}

请直接返回JSON，不要添加其他内容。
"""
        
        try:
            # 调用UFO³ Galaxy的LLM
            response = await self.bridge.simple_ask(prompt)
            
            # 解析JSON
            result = json.loads(response)
            
            return {
                "success": True,
                "nlu_result": result,
                "raw_response": response
}
        
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse LLM response",
                "raw_response": response if 'response' in dir() else None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ============ 使用示例 ============

async def example():
    """使用示例"""
    engine = WakeEngine()
    
    # 设置回调
    def on_wake(context):
        print(f"🎯 Wake from {context.source}: {context.raw_command}")
    
    def on_intent(context, intent):
        print(f"🧠 Intent: {intent.type.value} - {intent.action}")
        print(f"   Target: {intent.target}")
        print(f"   Parameters: {intent.parameters}")
    
    engine.set_callbacks(on_wake, on_intent)
    
    # 测试命令
    test_commands = [
        "嘿BLACK，帮我搜索今天的新闻",
        "打开微信",
        "帮我关闭浏览器",
        "截图",
        "写一段Python代码实现快速排序",
    ]
    
    for cmd in test_commands:
        result = await engine.process_wake(cmd, source="test")
        print(f"✅ Result: {result['success']}")
        print()


if __name__ == "__main__":
    asyncio.run(example())
