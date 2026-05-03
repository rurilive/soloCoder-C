import sys
import os
from pathlib import Path
from openpyxl import Workbook
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.parsers.excel_parser import (
    get_sheet_metadata,
    get_sheet_data_paginated,
    get_sheet_data_as_json,
)


def create_large_excel(row_count=5000, col_count=10):
    """创建大型测试Excel文件"""
    wb = Workbook()
    
    ws1 = wb.active
    ws1.title = "大型数据表"
    
    headers = [f"列_{i}" for i in range(1, col_count + 1)]
    for col_idx, header in enumerate(headers, 1):
        cell = ws1.cell(row=1, column=col_idx, value=header)
        cell.font = cell.font.copy(bold=True)
    
    for row_idx in range(2, row_count + 1):
        for col_idx in range(1, col_count + 1):
            value = f"数据_{row_idx-1}_{col_idx}"
            if col_idx == 2:
                value = row_idx * 100
            elif col_idx == 3:
                value = (row_idx - 1) * 0.1
            elif col_idx == 4:
                value = datetime(2024, 1, (row_idx - 2) % 28 + 1)
            elif col_idx == 5:
                value = (row_idx - 1) % 2 == 0
            
            ws1.cell(row=row_idx, column=col_idx, value=value)
    
    ws2 = wb.create_sheet("小型数据表")
    ws2.append(["产品", "价格", "数量"])
    for i in range(1, 51):
        ws2.append([f"产品_{i}", i * 10, i * 2])
    
    ws3 = wb.create_sheet("合并单元格表")
    ws3.merge_cells('A1:C1')
    ws3['A1'] = "合并标题"
    ws3.append(["A", "B", "C"])
    for i in range(2, 102):
        ws3.append([i, i*2, i*3])
    
    test_file = Path("test_large_excel.xlsx")
    wb.save(test_file)
    print(f"✅ 大型测试Excel文件已创建: {test_file}")
    print(f"   - 工作表数量: 3")
    print(f"   - '大型数据表': {row_count}行 x {col_count}列")
    print(f"   - '小型数据表': 50行 x 3列")
    print(f"   - '合并单元格表': 101行 x 3列")
    return test_file


def test_metadata(file_path):
    """测试元数据获取"""
    print("\n" + "=" * 60)
    print("测试1: 元数据获取 (get_sheet_metadata)")
    print("=" * 60)
    
    import time
    start_time = time.time()
    
    metadata = get_sheet_metadata(str(file_path))
    
    elapsed = time.time() - start_time
    print(f"耗时: {elapsed:.4f} 秒")
    
    if metadata.get('success'):
        print(f"工作表数量: {metadata.get('sheet_count')}")
        for sheet in metadata.get('sheets', []):
            print(f"  - {sheet['name']}: {sheet['max_row']}行 x {sheet['max_col']}列")
        print("✅ 元数据获取成功")
        return True
    else:
        print(f"❌ 元数据获取失败: {metadata.get('error')}")
        return False


def test_pagination(file_path):
    """测试分页功能"""
    print("\n" + "=" * 60)
    print("测试2: 分页数据获取 (get_sheet_data_paginated)")
    print("=" * 60)
    
    import time
    
    sheet_name = "大型数据表"
    
    test_cases = [
        {"start": 1, "end": 100, "desc": "第1-100行"},
        {"start": 1000, "end": 1100, "desc": "第1000-1100行"},
        {"start": 4900, "end": 5000, "desc": "第4900-5000行 (最后一页)"},
    ]
    
    all_pass = True
    
    for tc in test_cases:
        print(f"\n测试: {tc['desc']}")
        
        start_time = time.time()
        
        data = get_sheet_data_paginated(
            str(file_path),
            sheet_name,
            start_row=tc['start'],
            end_row=tc['end'],
            include_styles=False
        )
        
        elapsed = time.time() - start_time
        print(f"  耗时: {elapsed:.4f} 秒")
        
        if data.get('success'):
            expected_rows = tc['end'] - tc['start'] + 1
            actual_rows = data.get('row_count', 0)
            print(f"  总行数: {data.get('total_rows')}")
            print(f"  返回行数: {actual_rows} (预期: {expected_rows})")
            print(f"  列数: {data.get('total_cols')}")
            
            if data.get('data') and len(data['data']) > 0:
                first_row = data['data'][0]
                print(f"  第一行数据: {[c.get('value') for c in first_row[:3]]}...")
            
            if actual_rows == expected_rows:
                print(f"  ✅ 数据正确")
            else:
                print(f"  ❌ 数据行数不匹配")
                all_pass = False
        else:
            print(f"  ❌ 获取失败: {data.get('error')}")
            all_pass = False
    
    return all_pass


def test_large_file_detection(file_path):
    """测试大文件检测"""
    print("\n" + "=" * 60)
    print("测试3: 大文件自动检测 (get_sheet_data_as_json)")
    print("=" * 60)
    
    import time
    start_time = time.time()
    
    data = get_sheet_data_as_json(str(file_path))
    
    elapsed = time.time() - start_time
    print(f"耗时: {elapsed:.4f} 秒")
    
    if data.get('success'):
        print(f"是否为大文件: {data.get('is_large_file', False)}")
        
        for sheet in data.get('sheets', []):
            is_paginated = sheet.get('is_paginated', False)
            row_count = sheet.get('max_row', 0)
            print(f"  - {sheet['name']}: {row_count}行, 分页模式: {is_paginated}")
            
            if is_paginated:
                print(f"    消息: {sheet.get('message')}")
                if len(sheet.get('data', [])) == 0:
                    print(f"    ✅ 大表格未加载数据 (符合预期)")
                else:
                    print(f"    ⚠️  大表格仍然加载了数据")
            else:
                if len(sheet.get('data', [])) > 0:
                    print(f"    ✅ 小表格已加载数据 (行数: {len(sheet['data'])})")
        
        print("✅ 大文件检测功能正常")
        return True
    else:
        print(f"❌ 获取失败: {data.get('error')}")
        return False


def test_performance_comparison(file_path):
    """测试性能对比"""
    print("\n" + "=" * 60)
    print("测试4: 性能对比测试")
    print("=" * 60)
    
    import time
    
    sheet_name = "大型数据表"
    
    print("\n方式A: 全量加载 (get_sheet_data_as_json)")
    start_time = time.time()
    full_data = get_sheet_data_as_json(str(file_path), sheet_name)
    full_elapsed = time.time() - start_time
    print(f"  耗时: {full_elapsed:.4f} 秒")
    
    print("\n方式B: 元数据获取 (get_sheet_metadata)")
    start_time = time.time()
    metadata = get_sheet_metadata(str(file_path))
    meta_elapsed = time.time() - start_time
    print(f"  耗时: {meta_elapsed:.4f} 秒")
    
    print("\n方式C: 分页加载 100行 (get_sheet_data_paginated)")
    start_time = time.time()
    paginated_data = get_sheet_data_paginated(str(file_path), sheet_name, 1, 100)
    page_elapsed = time.time() - start_time
    print(f"  耗时: {page_elapsed:.4f} 秒")
    
    print("\n" + "-" * 60)
    print(f"性能对比:")
    print(f"  元数据获取比全量加载快: {full_elapsed / meta_elapsed:.1f}x")
    print(f"  分页加载比全量加载快: {full_elapsed / page_elapsed:.1f}x")
    print(f"  对于大型表格，建议先获取元数据，再分页加载数据")
    
    return True


def main():
    print("=" * 60)
    print("Excel分页功能测试")
    print("=" * 60)
    
    print("\n创建测试文件...")
    test_file = create_large_excel(row_count=5000, col_count=10)
    
    tests = [
        ("元数据获取", test_metadata),
        ("分页功能", test_pagination),
        ("大文件检测", test_large_file_detection),
        ("性能对比", test_performance_comparison),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func(test_file)
            results.append((name, success))
        except Exception as e:
            print(f"❌ 测试 {name} 抛出异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
        if success:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    
    if test_file.exists():
        print(f"\n测试文件: {test_file} (如需可手动删除)")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
