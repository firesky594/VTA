import os

# 强制开启 Windows 终端的 ANSI 颜色支持
os.system('')

class Color:
    GREEN = '\033[92m'   # 成功/加载
    CYAN = '\033[96m'    # 路径/信息
    YELLOW = '\033[93m'  # 警告
    RED = '\033[91m'     # 错误
    MAGENTA = '\033[95m' # 发现/AI分析
    END = '\033[0m'      # 重置颜色

def log_success(mod, msg=""):
    print(f"【S】{Color.GREEN}LOADED {mod:15} | {Color.CYAN}{msg}{Color.END}")
def log_error(mod, info="error", msg=""):
    print(f"【E】{Color.RED}ERROR {mod:15} | {Color.RED}{info}{Color.END} {msg}") 
def log_info(mod, info="info", msg=""):
    print(f"【I】{Color.GREEN}INFO {mod:15} | {Color.CYAN}{info}{Color.END} {msg}")
def log_ai(mod, info="ai", msg=""):
    print(f"【A】{Color.MAGENTA}AI {mod:15} | {Color.CYAN}{info}{Color.END} | {msg}")
