import pandas as pd
import os

# 创建示例数据
data = {
    '产品编号': ['PRD001', 'PRD002', 'PRD003', 'PRD004', 'PRD005'],
    '产品名称': ['笔记本电脑', '无线鼠标', '机械键盘', '显示器', 'USB 集线器'],
    '规格': ['15.6 英寸', '2.4GHz', '青轴', '27 英寸', '4 端口'],
    '价格': [5999, 199, 499, 1999, 89],
    '库存': [45, 120, 87, 23, 156],
    '分类': ['电脑配件', '外设', '外设', '显示设备', '配件']
}

# 创建 DataFrame
df = pd.DataFrame(data)

# 获取当前脚本目录
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
print(current_dir)
print(f'📁 后端目录: {backend_dir}')
# 保存为 Excel 文件
excel_path = os.path.join(backend_dir, 'data.xlsx')
df.to_excel(excel_path, index=False, sheet_name='产品列表')

print(f'✅ Excel 文件已创建: {excel_path}')
print(f'📊 数据行数: {len(df)}')
print(f'📋 列数: {len(df.columns)}')
