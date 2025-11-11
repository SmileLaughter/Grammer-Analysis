"""
文法类定义模块
用于表示上下文无关文法
"""

from typing import List, Set, Dict, Tuple


class Production:
    """产生式类"""
    
    def __init__(self, left: str, right: List[str], index: int = 0):
        """
        初始化产生式
        :param left: 产生式左部（非终结符）
        :param right: 产生式右部（符号列表）
        :param index: 产生式编号
        """
        self.left = left  # 左部非终结符
        self.right = right  # 右部符号列表
        self.index = index  # 产生式编号
    
    def __str__(self):
        """返回产生式的字符串表示"""
        right_str = ' '.join(self.right) if self.right else 'ε'
        return f"{self.left} → {right_str}"
    
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        """判断两个产生式是否相等"""
        if not isinstance(other, Production):
            return False
        return self.left == other.left and self.right == other.right
    
    def __hash__(self):
        """使产生式可哈希，以便在集合和字典中使用"""
        return hash((self.left, tuple(self.right)))
    
    def is_epsilon(self) -> bool:
        """判断产生式右部是否为空（epsilon产生式）"""
        return len(self.right) == 0 or (len(self.right) == 1 and self.right[0] == 'ε')


class Grammar:
    """文法类"""
    
    def __init__(self):
        """初始化文法"""
        self.productions: List[Production] = []  # 产生式列表
        self.non_terminals: Set[str] = set()  # 非终结符集合
        self.terminals: Set[str] = set()  # 终结符集合
        self.start_symbol: str = None  # 开始符号
    
    def add_production(self, left: str, right: List[str]):
        """
        添加产生式
        :param left: 产生式左部
        :param right: 产生式右部
        """
        # 创建产生式并添加到列表中
        index = len(self.productions)
        prod = Production(left, right, index)
        self.productions.append(prod)
        
        # 更新非终结符集合
        self.non_terminals.add(left)
        
        # 如果这是第一个产生式，设置开始符号
        if self.start_symbol is None:
            self.start_symbol = left
        
        # 更新终结符集合（右部中的小写字母和其他符号）
        for symbol in right:
            if symbol != 'ε' and symbol not in self.non_terminals:
                # 判断是否为终结符（不是非终结符且不是epsilon）
                if not self._is_non_terminal(symbol):
                    self.terminals.add(symbol)
    
    def _is_non_terminal(self, symbol: str) -> bool:
        """
        判断符号是否为非终结符
        非终结符通常是大写字母，或多个大写字母，或大写字母后跟单引号（prime）
        :param symbol: 待判断的符号
        :return: 是否为非终结符
        """
        if not symbol:
            return False
        
        # 所有字母都是大写（如 S, EP, TP, STMT 等）
        # 或者大写字母后跟单引号（如 S', A', E' 等）
        if symbol[0].isupper():
            # 检查是否全是大写字母或大写字母+单引号
            for i, c in enumerate(symbol):
                if not (c.isupper() or c == "'"):
                    return False
            return True
        
        return False
    
    def get_productions_for(self, non_terminal: str) -> List[Production]:
        """
        获取某个非终结符的所有产生式
        :param non_terminal: 非终结符
        :return: 产生式列表
        """
        return [p for p in self.productions if p.left == non_terminal]
    
    def __str__(self):
        """返回文法的字符串表示"""
        result = "文法产生式：\n"
        for prod in self.productions:
            result += f"  {prod}\n"
        return result
    
    def print_info(self):
        """打印文法的详细信息"""
        print("=" * 50)
        print("文法信息")
        print("=" * 50)
        print(f"开始符号: {self.start_symbol}")
        print(f"非终结符: {sorted(self.non_terminals)}")
        print(f"终结符: {sorted(self.terminals)}")
        print("\n产生式：")
        for i, prod in enumerate(self.productions):
            print(f"  ({i}) {prod}")
        print("=" * 50)
