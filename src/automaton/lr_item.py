"""
LR 项和项集类
用于 LR(0)、SLR、LR(1) 等分析算法
"""

from typing import List, Set, Optional
from src.core.grammar import Production


class LRItem:
    """
    LR(0) 项
    表示形式：A → α·β
    其中 · 表示当前位置
    """
    
    def __init__(self, production: Production, dot_position: int = 0):
        """
        初始化 LR 项
        :param production: 产生式
        :param dot_position: 点的位置（在产生式右部的索引）
        """
        self.production = production
        self.dot_position = dot_position
    
    @property
    def left(self) -> str:
        """获取产生式左部"""
        return self.production.left
    
    @property
    def right(self) -> List[str]:
        """获取产生式右部"""
        return self.production.right
    
    def is_reducible(self) -> bool:
        """
        判断是否是归约项（点在最右边）
        :return: 是否可归约
        """
        return self.dot_position >= len(self.right)
    
    def next_symbol(self) -> Optional[str]:
        """
        获取点后面的符号
        :return: 点后的符号，如果点在最右边则返回 None
        """
        if self.is_reducible():
            return None
        return self.right[self.dot_position]
    
    def advance(self) -> 'LRItem':
        """
        移动点的位置（向右移动一位）
        :return: 新的 LR 项
        """
        return LRItem(self.production, self.dot_position + 1)
    
    def __eq__(self, other):
        """判断两个项是否相等"""
        if not isinstance(other, LRItem):
            return False
        return (self.production == other.production and 
                self.dot_position == other.dot_position)
    
    def __hash__(self):
        """计算哈希值（用于集合和字典）"""
        return hash((self.production, self.dot_position))
    
    def __str__(self):
        """字符串表示"""
        # 构造右部，在适当位置插入点
        right_with_dot = list(self.right)
        right_with_dot.insert(self.dot_position, '·')
        right_str = ' '.join(right_with_dot) if right_with_dot else '·'
        return f"{self.left} → {right_str}"
    
    def __repr__(self):
        return self.__str__()


class ItemSet:
    """
    项集（状态）
    表示 LR 自动机中的一个状态
    """
    
    def __init__(self, items: Set[LRItem] = None, state_id: int = -1):
        """
        初始化项集
        :param items: LR 项的集合
        :param state_id: 状态编号
        """
        # 内部使用set保证唯一性，但在迭代时保证顺序
        self.items = items if items is not None else set()
        self.state_id = state_id
        self._sorted_cache = None  # 缓存排序后的项列表
    
    def add_item(self, item: LRItem):
        """
        添加一个项到项集
        :param item: LR 项
        """
        self.items.add(item)
        self._sorted_cache = None  # 清除缓存
    
    def _get_sorted_items(self):
        """
        获取排序后的项列表（用于保证迭代顺序的确定性）
        排序规则：按产生式索引、点位置、前看符号（如果有）排序
        """
        if self._sorted_cache is None:
            self._sorted_cache = sorted(
                self.items,
                key=lambda x: (
                    x.production.index,
                    x.dot_position,
                    getattr(x, 'lookahead', '')  # LR1Item才有lookahead
                )
            )
        return self._sorted_cache
    
    def __eq__(self, other):
        """判断两个项集是否相等（基于项的集合）"""
        if not isinstance(other, ItemSet):
            return False
        return self.items == other.items
    
    def __hash__(self):
        """计算哈希值"""
        return hash(frozenset(self.items))
    
    def __str__(self):
        """字符串表示"""
        # 使用排序后的项列表以保证输出顺序一致
        items_str = '\n  '.join(str(item) for item in self._get_sorted_items())
        return f"I{self.state_id}:\n  {items_str}"
    
    def __repr__(self):
        return f"ItemSet(id={self.state_id}, items={len(self.items)})"
    
    def __iter__(self):
        """支持迭代（根据配置决定是否使用确定性顺序）"""
        try:
            from src.config.dfa_config import dfa_config
            if dfa_config.is_deterministic():
                return iter(self._get_sorted_items())
        except ImportError:
            pass
        # 非确定性模式或配置不可用时，使用原始set迭代
        return iter(self.items)
    
    def __len__(self):
        """获取项集大小"""
        return len(self.items)


class LR1Item(LRItem):
    """
    LR(1) 项
    表示形式：[A → α·β, a]
    其中 a 是向前看符号
    """
    
    def __init__(self, production: Production, dot_position: int = 0, 
                 lookahead: str = '$'):
        """
        初始化 LR(1) 项
        :param production: 产生式
        :param dot_position: 点的位置
        :param lookahead: 向前看符号
        """
        super().__init__(production, dot_position)
        self.lookahead = lookahead
    
    def advance(self) -> 'LR1Item':
        """
        移动点的位置
        :return: 新的 LR(1) 项
        """
        return LR1Item(self.production, self.dot_position + 1, self.lookahead)
    
    def __eq__(self, other):
        """判断两个 LR(1) 项是否相等"""
        if not isinstance(other, LR1Item):
            return False
        return (self.production == other.production and 
                self.dot_position == other.dot_position and
                self.lookahead == other.lookahead)
    
    def __hash__(self):
        """计算哈希值"""
        return hash((self.production, self.dot_position, self.lookahead))
    
    def __str__(self):
        """字符串表示"""
        # 构造右部，在适当位置插入点
        right_with_dot = list(self.right)
        right_with_dot.insert(self.dot_position, '·')
        right_str = ' '.join(right_with_dot) if right_with_dot else '·'
        return f"[{self.left} → {right_str}, {self.lookahead}]"
