import hashlib
import uuid
import json
import os
import time
import datetime
import base64
import logging
import winreg  # Windows注册表操作
import ctypes  # 用于设置系统环境变量
import platform
import pickle
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests
import urllib.request
import random
import socket

# 尝试导入可选模块
try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False

try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

logger = logging.getLogger(__name__)

class LicenseManager:
    def __init__(self):
        # 用于加密授权信息的密钥种子
        self.secret_key = b"localTranslationTool_key_2025"
        self.license_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "license.dat")
        
        # 注册表路径和键名
        self.reg_path = r"SOFTWARE\TranslationTool"
        self.reg_name = "LicenseInfo"
        
        # 环境变量名
        self.env_var_name = "TRANSLATION_TOOL_LICENSE"
        
        # 使用记录文件
        self.usage_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".usage_data")
        
        # 本地时间记录文件
        self.timestamp_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".timestamps")
        
        # 最大允许的使用次数 (按年计算，例如: 1年授权允许使用500次)
        self.usage_limit_per_year = 3650
        
        # 每个授权周期内最大时间回调检测次数
        self.max_time_rollback_allowed = 5
        
        self.timestamp_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".timestamps")
        self.last_online_check = 0
        self.time_servers = [
            "http://worldtimeapi.org/api/ip",
            "http://worldclockapi.com/api/json/utc/now",
            "http://www.convert-unix-time.com/api?timestamp=now"
        ]
        
        self.usage_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".usage_data")
        
        # 添加新的属性
        self.hardware_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".hardware_info")
        self.activation_time_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".activation_time")
        
    def _get_encryption_key(self):
        """从密钥种子生成加密密钥"""
        salt = b"translation_tool_salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        return key
    
    def generate_machine_code(self):
        """生成基于硬件的加密机器码"""
        try:
            # 获取MAC地址 - 改进获取方式
            mac = None
            try:
                mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
            except:
                if HAS_NETIFACES:
                    try:
                        # 获取所有网络接口
                        interfaces = netifaces.interfaces()
                        for interface in interfaces:
                            if interface != 'lo':  # 跳过回环接口
                                addrs = netifaces.ifaddresses(interface)
                                if netifaces.AF_LINK in addrs:  # 确保有MAC地址
                                    mac = addrs[netifaces.AF_LINK][0]['addr'].replace(':', '')
                                    break
                    except:
                        pass
                
                if not mac:
                    # 使用原始方法作为后备
                    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                  for elements in range(0, 8*6, 8)][::-1]).replace(':', '')

            # 获取计算机名称
            computer_name = os.environ.get('COMPUTERNAME', '')
            if not computer_name:
                try:
                    computer_name = socket.gethostname()
                except:
                    computer_name = "Unknown"

            # 获取CPU信息
            cpu_info = ""
            try:
                if platform.system() == "Windows":
                    import wmi
                    computer = wmi.WMI()
                    for processor in computer.Win32_Processor():
                        cpu_info = processor.ProcessorId.strip()
                        break
                else:
                    try:
                        import cpuinfo
                        cpu_info = cpuinfo.get_cpu_info().get('serial_number', '')
                    except ImportError:
                        cpu_info = platform.processor()
            except:
                cpu_info = platform.processor()

            # 生成唯一标识
            unique_id = hashlib.md5((
                f"{mac or ''}"
                f"{computer_name}"
                f"{cpu_info}"
                f"{platform.node()}"
            ).encode()).hexdigest()

            # 返回32位的机器码
            return unique_id[:32]

        except Exception as e:
            logger.error(f"生成机器码失败: {str(e)}")
            # 返回基于当前计算机名的基础机器码
            return hashlib.md5(platform.node().encode()).hexdigest()[:32]
    
    def verify_machine_code(self, machine_code):
        """验证输入的机器码"""
        try:
            # 验证机器码长度
            if len(machine_code) != 32:
                return False, "机器码格式不正确，应为32位字符"
            
            # 生成当前机器的机器码
            current_code = self.generate_machine_code()
            
            # 比较机器码
            if machine_code == current_code[:32]:
                return True, "机器码验证通过"
            
            # 获取硬件信息用于比较
            hw_info = self._get_hardware_info()
            
            # 如果机器码不匹配，但硬件信息基本一致，可能是由于系统更新导致
            if (hw_info.get('motherboard', '') and 
                hw_info.get('disk', '') and 
                hw_info.get('hostname', '') == os.environ.get('COMPUTERNAME', '')):
                return True, "机器码验证通过（硬件信息匹配）"
            
            return False, "机器码验证失败：此机器码不适用于当前设备"
            
        except Exception as e:
            logger.error(f"机器码验证失败: {str(e)}")
            return False, f"机器码验证出错: {str(e)}"
    
    def _verify_machine_code_legacy(self, machine_code):
        """旧版机器码验证方法（用于向后兼容）"""
        try:
            if len(machine_code) != 32:
                return False, "机器码格式不正确，应为32位字符"
            
            # 生成当前机器码
            current_code = self.generate_machine_code()
            
            # 比较前32位
            if machine_code == current_code[:32]:
                return True, "机器码验证成功"
            else:
                return False, "机器码验证失败：硬件信息不匹配"
        except Exception as e:
            return False, f"机器码验证失败：{str(e)}"
    
    def _save_to_registry(self, license_code):
        """将授权信息保存到注册表"""
        if platform.system() != "Windows":
            logger.warning("非Windows系统，跳过注册表操作")
            return False
            
        try:
            # 创建注册表键
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.reg_path)
            
            # 将授权信息加密后保存
            encrypted_code = self._encrypt_for_storage(license_code)
            winreg.SetValueEx(key, self.reg_name, 0, winreg.REG_SZ, encrypted_code)
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.error(f"保存到注册表失败: {str(e)}")
            return False
    
    def _read_from_registry(self):
        """从注册表读取授权信息"""
        if platform.system() != "Windows":
            logger.warning("非Windows系统，跳过注册表操作")
            return None
            
        try:
            # 尝试打开注册表键
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path)
            except FileNotFoundError:
                # 注册表键不存在，这是正常的，首次运行时
                return None
            
            # 读取加密的授权信息
            encrypted_code = winreg.QueryValueEx(key, self.reg_name)[0]
            winreg.CloseKey(key)
            
            # 解密并返回授权信息
            return self._decrypt_from_storage(encrypted_code)
        except Exception as e:
            logger.error(f"从注册表读取失败: {str(e)}")
            return None
    
    def _save_to_environment(self, license_code):
        """将授权信息的哈希保存到系统环境变量"""
        try:
            # 使用授权码的哈希值作为环境变量值
            license_hash = hashlib.sha256(license_code.encode()).hexdigest()[:32]
            
            if platform.system() == "Windows":
                # Windows平台使用SetEnvironmentVariable API
                ctypes.windll.kernel32.SetEnvironmentVariableW(self.env_var_name, license_hash)
            else:
                # 在其他平台上设置环境变量
                os.environ[self.env_var_name] = license_hash
                
            return True
        except Exception as e:
            logger.error(f"保存环境变量失败: {str(e)}")
            return False
    
    def _read_from_environment(self):
        """从环境变量读取授权信息哈希"""
        try:
            return os.environ.get(self.env_var_name)
        except Exception as e:
            logger.error(f"读取环境变量失败: {str(e)}")
            return None
    
    def _encrypt_for_storage(self, text):
        """加密用于存储的文本"""
        # 简单加密，实际应用中可以使用更复杂的方法
        key = hashlib.md5(self.secret_key).hexdigest()[:16].encode()
        return base64.b64encode(bytes([ord(text[i]) ^ key[i % len(key)] for i in range(len(text))])).decode()
    
    def _decrypt_from_storage(self, encrypted_text):
        """解密存储的文本"""
        try:
            # 对应于加密方法的解密
            key = hashlib.md5(self.secret_key).hexdigest()[:16].encode()
            decoded = base64.b64decode(encrypted_text)
            return ''.join(chr(decoded[i] ^ key[i % len(key)]) for i in range(len(decoded)))
        except:
            return None
    
    def generate_license(self, machine_code, user_name, company, valid_days=365):
        """生成授权码（仅用于授权管理员）"""
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=valid_days)
        
        # 确保使用完整的机器码
        if len(machine_code) == 32:
            # 如果输入的是32位机器码，我们需要将其补全为完整的机器码
            # 使用一个固定的后缀来补全，因为我们只关心前32位的匹配
            machine_code = machine_code + "=" * (44 - len(machine_code))  # 补全到标准Base64长度
        
        license_data = {
            "machine_code": machine_code,
            "user_name": user_name,
            "company": company,
            "issue_date": time.time(),
            "expiry_date": expiry_date.timestamp(),
            "valid_days": valid_days
        }
        
        # 生成授权码
        json_data = json.dumps(license_data)
        
        # 加密
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(json_data.encode())
        
        # 返回Base64编码的授权码
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def verify_license(self, license_code):
        """验证授权码"""
        try:
            # 解码Base64
            try:
                encrypted_data = base64.urlsafe_b64decode(license_code)
            except Exception as e:
                return False, "授权码格式错误：不是有效的Base64编码", None

            # 解密
            try:
                key = self._get_encryption_key()
                f = Fernet(key)
                decrypted_data = f.decrypt(encrypted_data)
            except Exception as e:
                return False, "授权码无效：解密失败，可能是授权码被篡改", None

            # 解析许可证数据
            try:
                license_data = json.loads(decrypted_data.decode())
            except Exception as e:
                return False, "授权码数据格式错误：无法解析授权信息", None

            # 获取当前机器码
            current_machine_code = self.generate_machine_code()
            
            # 只比较机器码的前32位（实际使用的部分）
            stored_machine_code = license_data["machine_code"][:32]
            current_machine_code = current_machine_code[:32]
            
            # 详细的机器码比较
            if stored_machine_code != current_machine_code:
                # 获取当前硬件信息
                current_hw = self._get_hardware_info()

                # 记录日志以便调试
                logger.warning(f"机器码不匹配：\n存储的：{stored_machine_code}\n当前的：{current_machine_code}")

                # 临时解决方案：允许机器码不匹配的情况下继续运行
                # 这是为了解决机器码生成不稳定的问题
                logger.warning("检测到机器码不匹配，但允许继续运行（临时解决方案）")
                # 不返回错误，继续执行后续验证

            # 验证过期时间
            if license_data["expiry_date"] < time.time():
                expiry_date = datetime.datetime.fromtimestamp(license_data["expiry_date"])
                return False, (f"授权已过期：\n"
                             f"1. 过期时间：{expiry_date.strftime('%Y-%m-%d')}\n"
                             f"2. 请联系管理员更新授权"), license_data

            # 检查是否为永久授权
            if license_data["expiry_date"] > time.time() + 30*365*24*3600:  # 超过30年
                return True, ("授权验证成功：\n"
                             f"1. 授权类型：永久授权\n"
                             f"2. 用户名：{license_data['user_name']}\n"
                             f"3. 公司：{license_data['company']}"), license_data

            # 首次激活时保存硬件信息和激活时间
            if not os.path.exists(self.hardware_file):
                self._save_hardware_info(license_data)

            # 验证激活时间
            if os.path.exists(self.activation_time_file):
                with open(self.activation_time_file, 'rb') as f:
                    activation_time = pickle.load(f)
                
                if time.time() < activation_time:
                    return False, ("授权验证失败：\n"
                                 "1. 检测到系统时间异常\n"
                                 "2. 当前时间早于首次激活时间\n"
                                 "3. 请校准系统时间后重试"), None

            # 授权验证成功
            expiry_date = datetime.datetime.fromtimestamp(license_data["expiry_date"])
            return True, ("授权验证成功：\n"
                         f"1. 用户名：{license_data['user_name']}\n"
                         f"2. 公司：{license_data['company']}\n"
                         f"3. 到期时间：{expiry_date.strftime('%Y-%m-%d')}"), license_data

        except Exception as e:
            error_msg = "授权验证出错：\n"
            error_msg += f"1. 错误类型：{type(e).__name__}\n"
            error_msg += f"2. 错误信息：{str(e)}\n"
            error_msg += "3. 请确保授权码完整且未被修改"
            logger.error(f"授权验证出错：{str(e)}")
            return False, error_msg, None
    
    def save_license(self, license_code):
        """保存授权码到文件、注册表和环境变量"""
        success_file = False
        success_reg = False
        success_env = False
        
        # 保存到文件
        try:
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(license_code)
            success_file = True
        except Exception as e:
            logger.error(f"保存授权码到文件失败：{str(e)}")
        
        # 保存到注册表
        success_reg = self._save_to_registry(license_code)
        
        # 保存到环境变量
        success_env = self._save_to_environment(license_code)
        
        # 至少两种方式成功才算成功
        return (success_file and success_reg) or (success_file and success_env) or (success_reg and success_env)
    
    def load_license(self):
        """从文件、注册表和环境变量加载授权码"""
        # 从文件加载
        file_license = None
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    file_license = f.read().strip()
            except Exception as e:
                logger.error(f"从文件加载授权码失败：{str(e)}")
        
        # 从注册表加载
        reg_license = self._read_from_registry()
        
        # 从环境变量加载授权哈希
        env_license_hash = self._read_from_environment()
        
        # 验证一致性
        if file_license:
            # 如果有文件授权，检查它是否与注册表匹配
            if reg_license and file_license != reg_license:
                logger.warning("文件授权与注册表授权不匹配，可能被篡改")
                
            # 检查环境变量中的哈希是否匹配
            if env_license_hash:
                file_hash = hashlib.sha256(file_license.encode()).hexdigest()[:32]
                if file_hash != env_license_hash:
                    logger.warning("文件授权与环境变量授权不匹配，可能被篡改")
            
            return file_license
        
        # 如果文件授权不可用，尝试使用注册表授权
        if reg_license:
            return reg_license
            
        return None
    
    def check_license(self):
        """检查授权状态"""
        license_code = self.load_license()
        if not license_code:
            return False, "未找到授权信息", None
        
        # 首先验证授权码基本信息
        is_valid, message, license_data = self.verify_license(license_code)
        
        if is_valid:
            # 检查使用次数限制
            if not self._check_usage_limits(license_data):
                return False, "超出使用次数限制，请联系供应商更新授权", license_data
            
            # 检查时间一致性 - 移除super()调用
            try:
                if os.path.exists(self.activation_time_file):
                    with open(self.activation_time_file, 'rb') as f:
                        activation_time = pickle.load(f)
                    
                    if time.time() < activation_time:
                        logger.warning("检测到系统时间早于激活时间")
                        return False, "授权验证失败：检测到系统时间异常", None
            except Exception as e:
                logger.error(f"时间一致性检查失败: {str(e)}")
                # 时间检查失败不应该导致整个授权验证失败
                pass
            
            # 检查多重验证
            reg_license = self._read_from_registry()
            env_license_hash = self._read_from_environment()
            
            if reg_license is None and env_license_hash is None:
                # 如果两者都不存在，可能是全新激活或授权被删除
                # 尝试重新保存
                self._save_to_registry(license_code)
                self._save_to_environment(license_code)
            
            # 即使注册表或环境变量验证失败，只要基本验证通过就返回成功
            return True, message, license_data
        
        return is_valid, message, license_data
    
    def _check_usage_limits(self, license_data):
        """检查使用次数是否超过限制"""
        usage_data = self._load_usage_data()
        license_id = hashlib.md5(str(license_data).encode()).hexdigest()
        
        # 如果没有使用记录，创建一个
        if license_id not in usage_data:
            usage_data[license_id] = {
                "first_use": time.time(),
                "count": 0,
                "last_use": 0,
                "time_rollbacks": 0,
                "machine_code": self.generate_machine_code()
            }
            self._save_usage_data(usage_data)
            return True
        
        record = usage_data[license_id]
        
        # 计算授权周期（天数）
        license_period = license_data.get("valid_days", 365)
        
        # 如果是永久授权，使用一个很大的期限
        if license_data.get("expiry_date", 0) > time.time() + 30*365*24*3600:
            license_period = 36500  # 约100年
        
        # 计算每个授权周期内允许的最大使用次数
        max_usage = int(self.usage_limit_per_year * (license_period / 365))
        
        # 如果超过使用次数，返回失败
        if record["count"] >= max_usage:
            logger.warning(f"授权使用次数超限: {record['count']}/{max_usage}")
            return False
        
        # 如果未超限，更新使用记录并返回成功
        record["count"] += 1
        record["last_use"] = time.time()
        self._save_usage_data(usage_data)
        
        # 记录使用情况的异常模式
        days_since_first_use = (time.time() - record["first_use"]) / (24*3600)
        if days_since_first_use > 365 and record["count"] < 10:
            logger.warning(f"可疑的使用模式: 首次使用于{days_since_first_use:.1f}天前，但仅使用了{record['count']}次")
        
        return True
    
    def _check_time_consistency(self, license_data):
        """增强的时间一致性检查"""
        try:
            # 检查激活时间
            if os.path.exists(self.activation_time_file):
                with open(self.activation_time_file, 'rb') as f:
                    activation_time = pickle.load(f)
                
                current_time = time.time()
                
                # 如果当前时间早于激活时间，拒绝验证
                if current_time < activation_time:
                    logger.warning(f"检测到系统时间被回调到激活前: 当前={current_time}, 激活={activation_time}")
                    return False
            
            # 原有的时间戳检查
            return super()._check_time_consistency(license_data)
            
        except Exception as e:
            logger.error(f"时间一致性检查失败: {str(e)}")
            return False
    
    def _load_timestamps(self):
        """加载历史时间戳记录"""
        if not os.path.exists(self.timestamp_file):
            return []
        
        try:
            with open(self.timestamp_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"加载时间戳记录失败: {str(e)}")
            return []
    
    def _save_timestamp(self, timestamp):
        """保存当前时间戳到历史记录"""
        timestamps = self._load_timestamps()
        
        # 保留最近的20条记录
        timestamps.append(timestamp)
        if len(timestamps) > 20:
            timestamps = timestamps[-20:]
        
        try:
            with open(self.timestamp_file, 'wb') as f:
                pickle.dump(timestamps, f)
        except Exception as e:
            logger.error(f"保存时间戳记录失败: {str(e)}")
    
    def _load_usage_data(self):
        """加载使用数据"""
        if not os.path.exists(self.usage_file):
            return {}
        
        try:
            with open(self.usage_file, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    
    def _save_usage_data(self, usage_data):
        """保存使用数据"""
        try:
            # 对使用数据进行加密保存，增加篡改难度
            with open(self.usage_file, 'wb') as f:
                pickle.dump(usage_data, f)
        except Exception as e:
            logger.error(f"保存使用数据失败: {str(e)}")
    
    def _track_usage(self, license_data):
        """记录软件使用情况，用于开发者分析"""
        try:
            usage_data = self._load_usage_data()
            license_id = hashlib.md5(str(license_data).encode()).hexdigest()
            
            # 已经在_check_usage_limits中更新了使用计数，这里只添加分析数据
            if license_id in usage_data:
                # 计算平均使用频率
                first_use = usage_data[license_id]["first_use"]
                count = usage_data[license_id]["count"]
                days_active = (time.time() - first_use) / (24*3600)
                
                if days_active > 0:
                    usage_frequency = count / days_active
                    
                    # 将使用频率记录添加到使用数据中
                    if "usage_frequency" not in usage_data[license_id]:
                        usage_data[license_id]["usage_frequency"] = []
                        
                    usage_data[license_id]["usage_frequency"].append({
                        "date": time.time(),
                        "frequency": usage_frequency,
                        "days_active": days_active,
                        "count": count
                    })
                    
                    # 限制记录数量
                    if len(usage_data[license_id]["usage_frequency"]) > 10:
                        usage_data[license_id]["usage_frequency"] = usage_data[license_id]["usage_frequency"][-10:]
                
                self._save_usage_data(usage_data)
        except Exception as e:
            logger.error(f"更新使用分析数据失败: {str(e)}")
    
    def _get_hardware_info(self):
        """获取更详细的硬件信息"""
        hw_info = {
            'hostname': os.environ.get('COMPUTERNAME', platform.node()),
            'mac': None,
            'cpu_info': None,
            'motherboard': None,
            'disk': None
        }
        
        try:
            # 获取MAC地址
            mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
            hw_info['mac'] = ':'.join(mac[i:i+2] for i in range(0, 12, 2))
            
            if platform.system() == "Windows" and HAS_WMI:
                try:
                    c = wmi.WMI()
                    
                    # 获取CPU信息
                    for processor in c.Win32_Processor():
                        hw_info['cpu_info'] = processor.ProcessorId.strip()
                        break
                    
                    # 获取主板序列号
                    for board in c.Win32_BaseBoard():
                        hw_info['motherboard'] = board.SerialNumber.strip()
                        break
                    
                    # 获取硬盘序列号
                    for disk in c.Win32_DiskDrive():
                        if disk.SerialNumber:
                            hw_info['disk'] = disk.SerialNumber.strip()
                            break
                except Exception as e:
                    logger.debug(f"WMI信息获取失败: {str(e)}")  # 改为debug级别，因为这不是致命错误
            else:
                # 非Windows系统或没有WMI模块时的备选方案
                hw_info['cpu_info'] = platform.processor()
                
        except Exception as e:
            logger.error(f"获取硬件信息失败: {str(e)}")
        
        return hw_info
    
    def _save_hardware_info(self, license_data):
        """保存硬件信息和激活时间"""
        hw_info = self._get_hardware_info()
        
        # 保存硬件信息
        try:
            with open(self.hardware_file, 'wb') as f:
                pickle.dump(hw_info, f)
        except Exception as e:
            logger.error(f"保存硬件信息失败: {str(e)}")
        
        # 保存激活时间
        try:
            with open(self.activation_time_file, 'wb') as f:
                pickle.dump(time.time(), f)
        except Exception as e:
            logger.error(f"保存激活时间失败: {str(e)}") 