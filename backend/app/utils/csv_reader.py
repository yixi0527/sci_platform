"""
CSV 读取与预览工具
- 限制行数防止内存溢出
- 自动探测编码
- 返回列名与数据行
"""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional


def preview_csv(
    file_path: str,
    max_rows: int = 50,
    encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    预览 CSV 文件的前 N 行
    
    Args:
        file_path: CSV 文件的绝对路径
        max_rows: 最大读取行数（默认 50，最大限制 100）
        encoding: 文件编码（默认 utf-8）
    
    Returns:
        {
            "columns": List[str],  # 列名
            "rows": List[List[Any]],  # 数据行
            "total_rows": int  # 实际读取的行数
        }
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: CSV 解析失败或列名缺失
        PermissionError: 文件无访问权限
    """
    # 输入验证
    if not file_path:
        raise ValueError("file_path cannot be empty")
    
    # 限制最大行数
    max_rows = max(1, min(max_rows, 100))  # 确保至少读取 1 行
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    
    # 文件大小检查（防止加载超大文件）
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > 500:  # 限制 500MB
        raise ValueError(f"File too large ({file_size_mb:.1f}MB). Maximum allowed: 500MB")
    
    # 尝试多种编码
    encodings = [encoding, "utf-8-sig", "utf-8", "gbk", "gb2312", "latin-1"]
    last_error = None
    
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                
                # 读取列名
                try:
                    columns = next(reader)
                except StopIteration:
                    raise ValueError("CSV file is empty")
                
                if not columns:
                    raise ValueError("CSV header is empty")
                
                # 读取数据行
                rows = []
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    # 转换数据类型
                    converted_row = []
                    for cell in row:
                        converted_row.append(_convert_cell(cell))
                    rows.append(converted_row)
                
                return {
                    "columns": columns,
                    "rows": rows,
                    "total_rows": len(rows)
                }
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
            continue
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")
    
    # 所有编码都失败
    raise ValueError(f"Failed to decode file with encodings: {encodings}. Last error: {last_error}")


def _convert_cell(value: str) -> Any:
    """
    将 CSV 单元格值转换为合适的 Python 类型
    """
    if value == "" or value is None:
        return None
    
    # 尝试转换为数字
    try:
        # 尝试整数
        if "." not in value:
            return int(value)
        # 尝试浮点数
        return float(value)
    except ValueError:
        # 保持字符串
        return value.strip()


def detect_columns(
    file_path: str,
    encoding: str = "utf-8"
) -> List[str]:
    """
    仅读取 CSV 的列名（第一行）
    
    Args:
        file_path: CSV 文件路径
        encoding: 文件编码
    
    Returns:
        列名列表
    """
    result = preview_csv(file_path, max_rows=0, encoding=encoding)
    return result["columns"]
