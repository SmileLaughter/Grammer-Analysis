"""
DFA生成配置模块
用于控制DFA生成的确定性
"""


class DFAConfig:
    """DFA生成配置（全局单例）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # 默认使用确定性模式（固定的DFA）
        self.deterministic_mode = True
    
    def enable_deterministic_mode(self):
        """启用确定性模式（生成固定的DFA）"""
        self.deterministic_mode = True
    
    def disable_deterministic_mode(self):
        """禁用确定性模式（生成同构但可能不同的DFA）"""
        self.deterministic_mode = False
    
    def is_deterministic(self) -> bool:
        """检查是否启用确定性模式"""
        return self.deterministic_mode


# 全局配置实例
dfa_config = DFAConfig()
