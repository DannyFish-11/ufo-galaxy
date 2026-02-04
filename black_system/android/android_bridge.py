"""
Android Agent===

功能：
集成 Bridge
================Android设备到BLACK调度框架
提供统一的API接口控制Android设备

支持：
1. 应用管理（安装、卸载、启动）
2. 设备控制（点击、滑动、输入）
3. 屏幕操作（截图、录制）
4. 系统信息获取
5. 语音交互

作者：Matrix Agent
版本：1.0.0
日期：2026-02-04
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import base64
import io


class AndroidStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class AndroidDevice:
    """Android设备信息"""
    device_id: str
    name: str
    model: str
    android_version: str
    status: AndroidStatus
    ip_address: Optional[str] = None
    port: int = 5555
    capabilities: List[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "model": self.model,
            "android_version": self.android_version,
            "status": self.status.value,
            "ip_address": self.ip_address,
            "port": self.port,
            "capabilities": self.capabilities or []
        }


@dataclass
class AndroidApp:
    """Android应用信息"""
    package_name: str
    app_name: str
    version_name: str
    version_code: int
    is_system_app: bool
    
    def to_dict(self) -> Dict:
        return {
            "package_name": self.package_name,
            "app_name": self.app_name,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "is_system_app": self.is_system_app
        }


class AndroidBridge:
    """
    Android设备桥接器
    
    功能：
    1. 设备连接管理
    2. 应用生命周期管理
    3. 设备操作控制
    4. 屏幕和媒体操作
    5. 语音输入集成
    """
    
    def __init__(self, gateway_url: str = "http://localhost:9000"):
        self.gateway_url = gateway_url
        self.devices: Dict[str, AndroidDevice] = {}
        self.status = AndroidStatus.DISCONNECTED
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # 默认能力
        self.default_capabilities = [
            "app_management",
            "touch_control",
            "gesture_control",
            "text_input",
            "screenshot",
            "screen_recording",
            "file_transfer",
            "voice_input",
            "accessibility"
        ]
    
    async def connect(self) -> bool:
        """连接到Android设备（通过UFO³ Galaxy Gateway）"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # 通过Gateway测试Android连接
            # 实际通过Node 33 (ADB) 连接
            response = await self.http_client.post(
                f"{self.gateway_url}/api/node/call",
                json={
                    "node_id": "33",
                    "method": "list_devices",
                    "params": {}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                devices_data = data.get("devices", [])
                
                for dev_info in devices_data:
                    device = AndroidDevice(
                        device_id=dev_info.get("id", ""),
                        name=dev_info.get("name", "Android Device"),
                        model=dev_info.get("model", "Unknown"),
                        android_version=dev_info.get("version", "Unknown"),
                        status=AndroidStatus.CONNECTED,
                        ip_address=dev_info.get("ip"),
                        capabilities=self.default_capabilities
                    )
                    self.devices[device.device_id] = device
                
                self.status = AndroidStatus.CONNECTED
                print(f"✅ Android Bridge connected. Devices: {len(self.devices)}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to connect Android Bridge: {e}")
            self.status = AndroidStatus.ERROR
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            self.status = AndroidStatus.DISCONNECTED
            print("🔌 Android Bridge disconnected")
    
    async def get_devices(self) -> List[Dict]:
        """获取所有设备"""
        return [device.to_dict() for device in self.devices.values()]
    
    async def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "status": self.status.value,
            "devices_count": len(self.devices),
            "devices": [d.to_dict() for d in self.devices.values()],
            "timestamp": datetime.now().isoformat()
        }
    
    # ============ 设备控制 ============
    
    async def tap(self, x: int, y: int, device_id: str = None) -> Dict[str, Any]:
        """
        点击屏幕坐标
        
        Args:
            x: X坐标
            y: Y坐标
            device_id: 设备ID
        """
        return await self._call_android_api(
            "tap",
            {"x": x, "y": y, "device_id": device_id}
        )
    
    async def double_tap(self, x: int, y: int, device_id: str = None) -> Dict[str, Any]:
        """双击"""
        return await self._call_android_api(
            "double_tap",
            {"x": x, "y": y, "device_id": device_id}
        )
    
    async def long_press(self, x: int, y: int, duration: int = 1000, 
                        device_id: str = None) -> Dict[str, Any]:
        """
        长按
        
        Args:
            x: X坐标
            y: Y坐标
            duration: 按压时长（毫秒）
            device_id: 设备ID
        """
        return await self._call_android_api(
            "long_press",
            {"x": x, "y": y, "duration": duration, "device_id": device_id}
        )
    
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, 
                   duration: int = 300, device_id: str = None) -> Dict[str, Any]:
        """
        滑动
        
        Args:
            x1, y1: 起始坐标
            x2, y2: 结束坐标
            duration: 滑动时长（毫秒）
            device_id: 设备ID
        """
        return await self._call_android_api(
            "swipe",
            {
                "x1": x1, "y1": y1,
                "x2": x2, "y2": y2,
                "duration": duration,
                "device_id": device_id
            }
        )
    
    async def input_text(self, text: str, device_id: str = None) -> Dict[str, Any]:
        """
        输入文本
        
        Args:
            text: 要输入的文本
            device_id: 设备ID
        """
        return await self._call_android_api(
            "input_text",
            {"text": text, "device_id": device_id}
        )
    
    async def press_key(self, key_code: int, device_id: str = None) -> Dict[str, Any]:
        """
        按键
        
        Args:
            key_code: 按键代码
            device_id: 设备ID
        """
        return await self._call_android_api(
            "press_key",
            {"key_code": key_code, "device_id": device_id}
        )
    
    async def go_home(self, device_id: str = None) -> Dict[str, Any]:
        """返回主屏幕"""
        return await self._call_android_api(
            "go_home",
            {"device_id": device_id}
        )
    
    async def go_back(self, device_id: str = None) -> Dict[str, Any]:
        """返回"""
        return await self._call_android_api(
            "go_back",
            {"device_id": device_id}
        )
    
    async def open_recent(self, device_id: str = None) -> Dict[str, Any]:
        """打开最近任务"""
        return await self._call_android_api(
            "open_recent",
            {"device_id": device_id}
        )
    
    # ============ 应用管理 ============
    
    async def launch_app(self, package_name: str, 
                        device_id: str = None) -> Dict[str, Any]:
        """
        启动应用
        
        Args:
            package_name: 包名（如 com.tencent.mm）
            device_id: 设备ID
        """
        return await self._call_android_api(
            "launch_app",
            {"package": package_name, "device_id": device_id}
        )
    
    async def stop_app(self, package_name: str, 
                      device_id: str = None) -> Dict[str, Any]:
        """
        停止应用
        
        Args:
            package_name: 包名
            device_id: 设备ID
        """
        return await self._call_android_api(
            "stop_app",
            {"package": package_name, "device_id": device_id}
        )
    
    async def install_app(self, apk_path: str, 
                         device_id: str = None) -> Dict[str, Any]:
        """
        安装应用
        
        Args:
            apk_path: APK文件路径
            device_id: 设备ID
        """
        return await self._call_android_api(
            "install_app",
            {"apk": apk_path, "device_id": device_id}
        )
    
    async def uninstall_app(self, package_name: str, 
                          device_id: str = None) -> Dict[str, Any]:
        """
        卸载应用
        
        Args:
            package_name: 包名
            device_id: 设备ID
        """
        return await self._call_android_api(
            "uninstall_app",
            {"package": package_name, "device_id": device_id}
        )
    
    async def list_apps(self, system_apps: bool = False, 
                       device_id: str = None) -> List[Dict]:
        """
        列出应用
        
        Args:
            system_apps: 是否包含系统应用
            device_id: 设备ID
        """
        result = await self._call_android_api(
            "list_apps",
            {"include_system": system_apps, "device_id": device_id}
        )
        return result.get("apps", [])
    
    # ============ 屏幕操作 ============
    
    async def screenshot(self, device_id: str = None) -> Dict[str, Any]:
        """
        截图
        
        Returns:
            base64编码的图像数据
        """
        return await self._call_android_api(
            "screenshot",
            {"device_id": device_id}
        )
    
    async def screen_record(self, duration: int = 30, 
                           device_id: str = None) -> Dict[str, Any]:
        """
        屏幕录制
        
        Args:
            duration: 录制时长（秒）
            device_id: 设备ID
        """
        return await self._call_android_api(
            "screen_record",
            {"duration": duration, "device_id": device_id}
        )
    
    async def get_screen_size(self, device_id: str = None) -> Dict[str, Any]:
        """获取屏幕尺寸"""
        return await self._call_android_api(
            "get_screen_size",
            {"device_id": device_id}
        )
    
    # ============ 文件操作 ============
    
    async def pull_file(self, remote_path: str, 
                       local_path: str = None,
                       device_id: str = None) -> Dict[str, Any]:
        """
        拉取文件

        Args:
            remote_path: 设备上的文件路径
            local_path: 本地保存路径
            device_id: 设备ID
        """
        return await self._call_android_api(
            "pull_file",
            {"remote": remote_path, "local": local_path, "device_id": device_id}
        )
    
    async def push_file(self, local_path: str, 
                       remote_path: str = None,
                       device_id: str = None) -> Dict[str, Any]:
        """
        推送文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 设备上的目标路径
            device_id: 设备ID
        """
        return await self._call_android_api(
            "push_file",
            {"local": local_path, "remote": remote_path, "device_id": device_id}
        )
    
    # ============ 系统信息 ============
    
    async def get_device_info(self, device_id: str = None) -> Dict[str, Any]:
        """获取设备信息"""
        return await self._call_android_api(
            "device_info",
            {"device_id": device_id}
        )
    
    async def get_battery(self, device_id: str = None) -> Dict[str, Any]:
        """获取电池信息"""
        return await self._call_android_api(
            "battery",
            {"device_id": device_id}
        )
    
    async def get_wifi_status(self, device_id: str = None) -> Dict[str, Any]:
        """获取WiFi状态"""
        return await self._call_android_api(
            "wifi_status",
            {"device_id": device_id}
        )
    
    # ============ 高级操作 ============
    
    async def find_element(self, strategy: str, value: str,
                          device_id: str = None) -> Dict[str, Any]:
        """
        查找界面元素
        
        Args:
            strategy: 查找策略（text, id, class, xpath）
            value: 元素值
            device_id: 设备ID
        """
        return await self._call_android_api(
            "find_element",
            {"strategy": strategy, "value": value, "device_id": device_id}
        )
    
    async def get_ui_tree(self, device_id: str = None) -> Dict[str, Any]:
        """获取UI树"""
        return await self._call_android_api(
            "ui_tree",
            {"device_id": device_id}
        )
    
    async def execute_automation(self, steps: List[Dict], 
                                device_id: str = None) -> List[Dict]:
        """
        执行自动化步骤
        
        Args:
            steps: 步骤列表 [{"action": "tap", "x": 100, "y": 200}]
            device_id: 设备ID
        """
        return await self._call_android_api(
            "execute_automation",
            {"steps": steps, "device_id": device_id}
        )
    
    # ============ 内部方法 ============
    
    async def _call_android_api(self, method: str, params: Dict) -> Dict[str, Any]:
        """调用Android API（通过UFO³ Galaxy Gateway）"""
        try:
            response = await self.http_client.post(
                f"{self.gateway_url}/api/node/call",
                json={
                    "node_id": "33",  # ADB节点
                    "method": method,
                    "params": params
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_default_device(self) -> Optional[str]:
        """获取默认设备ID"""
        if self.devices:
            return list(self.devices.keys())[0]
        return None


# ============ 便捷函数 ============

async def create_bridge(gateway_url: str = "http://localhost:9000") -> AndroidBridge:
    """创建并连接桥接器"""
    bridge = AndroidBridge(gateway_url)
    await bridge.connect()
    return bridge


# ============ 使用示例 ============

async def example():
    """使用示例"""
    bridge = await create_bridge()
    
    # 获取设备列表
    devices = await bridge.get_devices()
    print(f"Devices: {len(devices)}")
    
    # 启动应用
    await bridge.launch_app("com.tencent.mm")  # 微信
    
    # 截图
    screenshot = await bridge.screenshot()
    print(f"Screenshot size: {len(screenshot.get('data', ''))} bytes")
    
    # 断开连接
    await bridge.disconnect()


if __name__ == "__main__":
    asyncio.run(example())
