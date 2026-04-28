import sys
import traceback

print("=" * 60)
print("检查可用的文档解析包")
print("=" * 60)

# 1. 检查 python-docx
print("\n1. 检查 python-docx...")
try:
    import docx
    print(f"   ✅ python-docx 已安装")
    print(f"   版本: {docx.__version__ if hasattr(docx, '__version__') else '未知'}")
except ImportError as e:
    print(f"   ❌ python-docx 未安装: {e}")

# 2. 检查 pyantiword
print("\n2. 检查 pyantiword...")
try:
    from pyantiword import antiword_wrapper
    print(f"   ✅ pyantiword 已安装")
    print(f"   函数: {[x for x in dir(antiword_wrapper) if not x.startswith('_')]}")
except ImportError as e:
    print(f"   ❌ pyantiword 未安装: {e}")

# 3. 检查 mammoth（docx to html）
print("\n3. 检查 mammoth...")
try:
    import mammoth
    print(f"   ✅ mammoth 已安装")
    print(f"   版本: {mammoth.__version__ if hasattr(mammoth, '__version__') else '未知'}")
except ImportError as e:
    print(f"   ⚠️ mammoth 未安装: {e}")
    print("   提示: 可以用 'uv add mammoth' 安装，用于将 docx 转换为 html")

# 4. 检查 pypandoc
print("\n4. 检查 pypandoc...")
try:
    import pypandoc
    print(f"   ✅ pypandoc 已安装")
except ImportError as e:
    print(f"   ⚠️ pypandoc 未安装: {e}")

# 5. 检查 python-pptx（已安装）
print("\n5. 检查 python-pptx...")
try:
    from pptx import Presentation
    print(f"   ✅ python-pptx 已安装")
except ImportError as e:
    print(f"   ❌ python-pptx 未安装: {e}")

# 6. 检查 openpyxl（已安装）
print("\n6. 检查 openpyxl...")
try:
    import openpyxl
    print(f"   ✅ openpyxl 已安装")
    print(f"   版本: {openpyxl.__version__ if hasattr(openpyxl, '__version__') else '未知'}")
except ImportError as e:
    print(f"   ❌ openpyxl 未安装: {e}")

# 7. 检查 libreoffice（系统级工具）
print("\n7. 检查 libreoffice...")
import subprocess
try:
    result = subprocess.run(['libreoffice', '--version'], capture_output=True, text=True, timeout=10)
    print(f"   ✅ libreoffice 已安装")
    print(f"   输出: {result.stdout or result.stderr}")
except FileNotFoundError:
    print(f"   ⚠️ libreoffice 未安装")
    print("   提示: 可以用 'sudo apt install libreoffice' 安装，用于转换各种 Office 格式")
except Exception as e:
    print(f"   ⚠️ 检查 libreoffice 出错: {e}")

print("\n" + "=" * 60)
print("建议的改进方案")
print("=" * 60)
print("""
方案 A：使用 mammoth（推荐用于 docx）
  - 优点：可以将 docx 转换为 HTML，保留格式（标题、列表、表格、加粗、斜体等）
  - 安装：uv add mammoth
  - 限制：只支持 .docx，不支持 .doc

方案 B：使用 libreoffice（推荐用于 doc）
  - 优点：可以将 .doc 转换为 .docx 或 .html，保留格式
  - 安装：sudo apt install libreoffice
  - 限制：需要系统级安装，调用较慢

方案 C：组合方案（推荐）
  - .docx 文件：使用 python-docx + mammoth（保留更多格式）
  - .doc 文件：使用 pyantiword + 自定义解析（或 libreoffice）
  - 添加详细的 debug 日志

当前可用的包：
  ✅ python-docx - 用于 .docx（但格式提取有限）
  ✅ pyantiword - 用于 .doc（纯文本）
  ❌ mammoth - 未安装（推荐安装）
  ❌ libreoffice - 未安装（可选）
""")
