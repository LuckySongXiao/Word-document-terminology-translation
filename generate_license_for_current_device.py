#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为当前设备生成授权码
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def generate_license_for_current_device():
    """为当前设备生成授权码"""
    print("=== 为当前设备生成授权码 ===")
    
    try:
        from utils.license import LicenseManager
        
        license_manager = LicenseManager()
        
        # 1. 获取当前设备的机器码
        print("1. 获取当前设备机器码...")
        current_machine_code = license_manager.generate_machine_code()
        print(f"   当前机器码: {current_machine_code}")
        
        # 2. 生成授权码
        print("2. 生成授权码...")
        license_code = license_manager.generate_license(
            machine_code=current_machine_code,
            user_name="精神抖擞",
            company="精神抖擞",
            valid_days=36500  # 100年，相当于永久授权
        )
        print(f"   授权码生成成功")
        print(f"   授权码长度: {len(license_code)}")
        
        # 3. 验证授权码
        print("3. 验证授权码...")
        is_valid, message, license_data = license_manager.verify_license(license_code)
        print(f"   验证结果: {'有效' if is_valid else '无效'}")
        print(f"   验证消息: {message}")
        
        if is_valid:
            # 4. 保存授权码
            print("4. 保存授权码...")
            if license_manager.save_license(license_code):
                print("   授权码保存成功")
                
                # 5. 最终验证
                print("5. 最终验证...")
                final_valid, final_message, final_data = license_manager.check_license()
                print(f"   最终结果: {'有效' if final_valid else '无效'}")
                print(f"   最终消息: {final_message}")
                
                if final_valid:
                    print("\n✅ 授权生成和验证成功！")
                    print(f"授权码: {license_code}")
                    return True
                else:
                    print("\n❌ 最终验证失败")
                    return False
            else:
                print("   授权码保存失败")
                return False
        else:
            print("\n❌ 授权码验证失败")
            return False
            
    except Exception as e:
        print(f"生成授权码时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_license_for_current_device()
    if success:
        print("\n现在可以正常运行主程序了！")
    else:
        print("\n授权生成失败，请检查错误信息")
