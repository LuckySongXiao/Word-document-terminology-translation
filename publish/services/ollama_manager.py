import subprocess
import json
import logging
import psutil
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

class OllamaManager:
    def __init__(self):
        self.api_url = "http://localhost:11434/api"
        
    def check_ollama_running(self) -> bool:
        """检查Ollama服务是否运行"""
        try:
            response = requests.get(f"{self.api_url}/tags")
            return response.status_code == 200
        except:
            return False
            
    def get_installed_models(self) -> List[str]:
        """获取已安装的模型列表"""
        try:
            # 使用subprocess运行ollama list命令
            process = subprocess.Popen(
                ["ollama", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output, error = process.communicate()
            
            if process.returncode == 0:
                # 解析输出获取模型名称
                models = []
                for line in output.split('\n')[1:]:  # 跳过标题行
                    if line.strip():
                        # 第一列是模型名称
                        model_name = line.split()[0]
                        models.append(model_name)
                logger.info(f"已安装的模型: {models}")
                return models
            else:
                logger.error(f"获取模型列表失败: {error}")
                return []
        except Exception as e:
            logger.error(f"获取模型列表出错: {str(e)}")
            return []
    
    def get_system_info(self) -> Dict:
        """获取系统硬件信息"""
        return {
            'memory': psutil.virtual_memory().total / (1024**3),  # GB
            'cpu_count': psutil.cpu_count(),
            'gpu_available': self._check_gpu_available()
        }
    
    def _check_gpu_available(self) -> bool:
        """检查是否有可用的GPU"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def get_recommended_model(self) -> str:
        """根据系统配置推荐合适的模型"""
        sys_info = self.get_system_info()
        installed_models = self.get_installed_models()
        
        # 根据系统配置推荐模型
        recommended_models = []
        if sys_info['gpu_available'] and sys_info['memory'] >= 16:
            recommended_models = ["qwen:7b", "qwen2.5:0.5b", "llama2"]
        else:
            recommended_models = ["qwen2.5:0.5b", "llama2"]
        
        # 返回第一个已安装的推荐模型，如果没有则返回任意已安装模型
        for model in recommended_models:
            if model in installed_models:
                return model
        return installed_models[0] if installed_models else "qwen2.5:0.5b"
    
    def pull_model(self, model_name: str) -> bool:
        """拉取指定的模型"""
        try:
            logger.info(f"开始拉取模型: {model_name}")
            
            # 使用subprocess运行ollama命令
            try:
                # 首先尝试使用ollama pull
                process = subprocess.Popen(
                    ["ollama", "pull", model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                while True:
                    output = process.stdout.readline()
                    if output:
                        logger.info(f"拉取进度: {output.strip()}")
                    if process.poll() is not None:
                        break
                
                if process.returncode != 0:
                    # 如果pull失败，尝试使用run命令
                    logger.info(f"使用 ollama run 命令拉取模型: {model_name}")
                    process = subprocess.Popen(
                        ["ollama", "run", model_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    # 等待几秒后终止进程
                    import time
                    time.sleep(5)
                    process.terminate()
                
                return True
                
            except subprocess.CalledProcessError as e:
                logger.error(f"执行ollama命令失败: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"拉取模型失败: {str(e)}")
            return False

def setup_ollama() -> List[str]:
    """设置Ollama环境并返回可用的模型列表"""
    manager = OllamaManager()
    
    if not manager.check_ollama_running():
        logger.warning("Ollama服务未运行")
        return []
    
    installed_models = manager.get_installed_models()
    recommended_model = manager.get_recommended_model()
    
    if recommended_model not in installed_models:
        logger.info(f"推荐的模型 {recommended_model} 未安装，开始拉取...")
        if manager.pull_model(recommended_model):
            installed_models.append(recommended_model)
            logger.info(f"模型 {recommended_model} 拉取成功")
        else:
            logger.error(f"模型 {recommended_model} 拉取失败")
    
    return installed_models 