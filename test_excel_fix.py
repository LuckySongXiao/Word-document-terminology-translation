#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Excel处理修复的脚本
创建一个简单的Excel文件用于测试C#版本的Excel处理功能
"""

import openpyxl
import os

def create_test_excel():
    """创建测试用的Excel文件"""
    # 创建工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "测试工作表"
    
    # 添加测试数据
    test_data = [
        ["产品名称", "价格", "描述"],
        ["苹果", "5.00", "新鲜的红苹果"],
        ["香蕉", "3.50", "进口香蕉，营养丰富"],
        ["橙子", "4.20", "维生素C含量高"],
        ["葡萄", "8.00", "无籽葡萄，口感甜美"],
        ["草莓", "12.00", "有机草莓，天然无污染"]
    ]
    
    # 写入数据
    for row_idx, row_data in enumerate(test_data, 1):
        for col_idx, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=cell_value)
    
    # 设置列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 25
    
    # 保存文件
    output_path = "测试Excel文件.xlsx"
    wb.save(output_path)
    print(f"✅ 测试Excel文件已创建: {output_path}")
    return output_path

if __name__ == "__main__":
    try:
        excel_file = create_test_excel()
        print(f"📁 文件位置: {os.path.abspath(excel_file)}")
        print("🔧 现在可以使用C#版本测试Excel翻译功能了")
        print("📋 测试步骤:")
        print("   1. 运行C#版本程序")
        print("   2. 选择刚创建的Excel文件")
        print("   3. 选择翻译引擎和目标语言")
        print("   4. 开始翻译")
        print("   5. 检查是否不再出现内容类型错误")
    except Exception as e:
        print(f"❌ 创建测试文件失败: {e}")
