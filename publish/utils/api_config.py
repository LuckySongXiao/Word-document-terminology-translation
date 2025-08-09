import os
import json
import logging

logger = logging.getLogger(__name__)

class APIConfig:
    def __init__(self):
        self.config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.api_config_path = os.path.join(self.config_dir, "api_history.json")
        self.api_history = self.load_api_history()

    def load_api_history(self):
        """加载API历史记录"""
        try:
            if os.path.exists(self.api_config_path):
                with open(self.api_config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('api_history', [])
            return ["http://localhost:11434"]  # 默认值
        except Exception as e:
            logger.error(f"加载API历史记录失败: {str(e)}")
            return ["http://localhost:11434"]

    def save_api_history(self, api_history):
        """保存API历史记录"""
        try:
            with open(self.api_config_path, 'w', encoding='utf-8') as f:
                json.dump({'api_history': api_history}, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"保存API历史记录失败: {str(e)}")
            return False

    def add_api_url(self, url):
        """添加新的API地址到历史记录"""
        if url not in self.api_history:
            self.api_history.insert(0, url)
            if len(self.api_history) > 10:  # 限制最多保存10个地址
                self.api_history.pop()
        else:
            # 如果地址已存在，将其移到最前面
            self.api_history.remove(url)
            self.api_history.insert(0, url)
        return self.save_api_history(self.api_history) 