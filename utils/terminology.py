import json
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

# 获取程序根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 获取术语库文件路径
TERMINOLOGY_PATH = os.path.join(ROOT_DIR, 'terminology.json')
# 如果文件路径不存在，使用data目录下的terminology.json
if not os.path.exists(TERMINOLOGY_PATH):
    TERMINOLOGY_PATH = os.path.join(ROOT_DIR, 'data', 'terminology.json')

def load_terminology() -> Dict:
    """加载术语表"""
    try:
        # 使用验证器确保术语库结构正确
        from utils.terminology_validator import TerminologyValidator
        validator = TerminologyValidator()

        if not os.path.exists(TERMINOLOGY_PATH):
            # 如果文件不存在，创建默认术语库
            default_terminology = {
                "英语": {},
                "日语": {},
                "韩语": {},
                "德语": {},
                "法语": {},
                "西班牙语": {}
            }
            # 确保目录存在
            os.makedirs(os.path.dirname(TERMINOLOGY_PATH), exist_ok=True)
            with open(TERMINOLOGY_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_terminology, f, ensure_ascii=False, indent=2)
            logger.info("已创建默认术语库文件")
            return default_terminology

        # 验证并修复术语库文件
        validator.validate_and_fix_file(TERMINOLOGY_PATH)

        # 加载术语库
        with open(TERMINOLOGY_PATH, 'r', encoding='utf-8') as f:
            terminology = json.load(f)

            # 兼容旧版格式，如果有"中文"这一层，则取其下内容
            if "中文" in terminology:
                logger.info("检测到旧版术语库格式，正在转换...")
                old_terminology = terminology["中文"]
                # 修复结构
                fixed_terminology = validator.fix_terminology_structure(old_terminology)
                # 保存修复后的结构
                save_terminology(fixed_terminology)
                return fixed_terminology
            else:
                # 验证当前结构
                is_valid, errors = validator.validate_terminology_structure(terminology)
                if not is_valid:
                    logger.warning(f"术语库结构有问题，正在修复: {errors}")
                    fixed_terminology = validator.fix_terminology_structure(terminology)
                    save_terminology(fixed_terminology)
                    return fixed_terminology
                return terminology

    except Exception as e:
        logger.error(f"加载术语表失败: {str(e)}")
        # 返回默认结构
        return {"英语": {}, "日语": {}, "韩语": {}, "德语": {}, "法语": {}, "西班牙语": {}}

def save_terminology(terminology: Dict) -> None:
    """保存术语库到文件"""
    try:
        # 直接保存术语库，不再添加"中文"这一层
        os.makedirs(os.path.dirname(TERMINOLOGY_PATH), exist_ok=True)
        with open(TERMINOLOGY_PATH, 'w', encoding='utf-8') as f:
            json.dump(terminology, f, ensure_ascii=False, indent=2)
        logger.info(f"术语库已保存到: {TERMINOLOGY_PATH}")
    except Exception as e:
        logger.error(f"保存术语库失败：{str(e)}")
        raise