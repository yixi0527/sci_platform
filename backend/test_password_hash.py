"""
测试脚本：生成密码哈希
用法: python test_password_hash.py
输入明文密码，返回bcrypt哈希后的密码
"""
from passlib.context import CryptContext

# 使用与后端相同的密码上下文配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_password_hash(plain_password: str) -> str:
    """
    生成密码的bcrypt哈希值
    
    Args:
        plain_password: 明文密码
        
    Returns:
        哈希后的密码字符串
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        True 如果匹配，否则 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def main():
    print("=" * 60)
    print("密码哈希生成工具")
    print("=" * 60)
    print()
    
    # 获取用户输入
    plain_password = input("请输入明文密码: ").strip()
    
    if not plain_password:
        print("错误: 密码不能为空！")
        return
    
    print()
    print("正在生成哈希密码...")
    
    # 生成哈希
    hashed_password = generate_password_hash(plain_password)
    
    print()
    print("=" * 60)
    print("生成结果:")
    print("=" * 60)
    print(f"明文密码: {plain_password}")
    print(f"哈希密码: {hashed_password}")
    print()
    
    # 验证哈希
    print("验证哈希密码...")
    is_valid = verify_password(plain_password, hashed_password)
    
    if is_valid:
        print("✓ 验证成功！哈希密码与明文密码匹配")
    else:
        print("✗ 验证失败！")
    
    print()
    print("=" * 60)
    print("提示: 将哈希密码复制到数据库的 passwordHash 字段中")
    print("=" * 60)


def batch_generate():
    """批量生成多个密码的哈希"""
    print("=" * 60)
    print("批量密码哈希生成工具")
    print("=" * 60)
    print("输入密码列表，每行一个密码，输入空行结束")
    print()
    
    passwords = []
    while True:
        pwd = input(f"密码 #{len(passwords) + 1} (回车结束): ").strip()
        if not pwd:
            break
        passwords.append(pwd)
    
    if not passwords:
        print("未输入任何密码")
        return
    
    print()
    print("=" * 60)
    print("生成结果:")
    print("=" * 60)
    
    for i, pwd in enumerate(passwords, 1):
        hashed = generate_password_hash(pwd)
        print(f"\n{i}. 明文: {pwd}")
        print(f"   哈希: {hashed}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--batch":
            batch_generate()
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("用法:")
            print("  python test_password_hash.py          # 单个密码生成")
            print("  python test_password_hash.py --batch  # 批量密码生成")
            print("  python test_password_hash.py --help   # 显示帮助")
        else:
            # 直接从命令行参数获取密码
            plain_password = sys.argv[1]
            hashed_password = generate_password_hash(plain_password)
            print(f"明文密码: {plain_password}")
            print(f"哈希密码: {hashed_password}")
    else:
        # 交互式模式
        main()
