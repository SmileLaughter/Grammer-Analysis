"""
通用推导生成器
使用回溯搜索生成最左推导和最右推导，不依赖LL(1)或LR(1)限制
"""

from typing import List, Tuple, Optional
from src.core.grammar import Grammar, Production


class UniversalDerivationGenerator:
    """通用推导生成器（支持任意上下文无关文法）"""
    
    def __init__(self, grammar: Grammar, max_depth: int = 100):
        """
        初始化生成器
        :param grammar: 文法
        :param max_depth: 最大推导深度（防止无限递归）
        """
        self.grammar = grammar
        self.max_depth = max_depth
    
    def generate_leftmost_derivation(self, target: List[str]) -> Tuple[bool, List[Tuple[List[str], Optional[Production]]]]:
        """
        生成最左推导（使用回溯搜索）
        :param target: 目标句子
        :return: (是否成功, 推导步骤列表)，每个步骤是(句型, 使用的产生式)
        """
        # 初始句型
        initial = [self.grammar.start_symbol]
        
        # 使用回溯搜索
        result = self._search_leftmost(initial, target, 0, [])
        
        if result is None:
            return False, []
        
        # 添加初始步骤
        steps = [(initial, None)] + result
        return True, steps
    
    def _search_leftmost(self, current: List[str], target: List[str], 
                        depth: int, path: List) -> Optional[List]:
        """
        回溯搜索最左推导
        :param current: 当前句型
        :param target: 目标句子
        :param depth: 当前深度
        :param path: 已走过的路径
        :return: 推导步骤列表，失败返回None
        """
        # 检查是否达到目标
        if current == target:
            return []
        
        # 检查深度限制
        if depth >= self.max_depth:
            return None
        
        # 检查是否所有符号都是终结符
        all_terminals = all(s in self.grammar.terminals for s in current)
        if all_terminals and current != target:
            # 已经全是终结符但不匹配目标，失败
            return None
        
        # 如果当前句型长度已经超过目标，且无法继续匹配
        if len(current) > len(target):
            # 检查前缀是否匹配
            terminal_count = sum(1 for s in current if s in self.grammar.terminals)
            if terminal_count > len(target):
                return None
        
        # 找到最左边的非终结符
        leftmost_pos = -1
        leftmost_nt = None
        for i, symbol in enumerate(current):
            if symbol in self.grammar.non_terminals:
                leftmost_pos = i
                leftmost_nt = symbol
                break
        
        if leftmost_nt is None:
            # 没有非终结符了
            return None
        
        # 尝试该非终结符的所有产生式
        for production in self.grammar.productions:
            if production.left != leftmost_nt:
                continue
            
            # 应用产生式
            new_current = current[:leftmost_pos]
            if not production.is_epsilon():
                new_current.extend(production.right)
            new_current.extend(current[leftmost_pos + 1:])
            
            # 递归搜索
            result = self._search_leftmost(new_current, target, depth + 1, path + [(new_current, production)])
            
            if result is not None:
                # 找到解
                return [(new_current, production)] + result
        
        # 所有产生式都失败
        return None
    
    def generate_rightmost_derivation(self, target: List[str]) -> Tuple[bool, List[Tuple[List[str], Optional[Production]]]]:
        """
        生成最右推导（使用回溯搜索）
        :param target: 目标句子
        :return: (是否成功, 推导步骤列表)
        """
        # 初始句型
        initial = [self.grammar.start_symbol]
        
        # 使用回溯搜索
        result = self._search_rightmost(initial, target, 0, [])
        
        if result is None:
            return False, []
        
        # 添加初始步骤
        steps = [(initial, None)] + result
        return True, steps
    
    def _search_rightmost(self, current: List[str], target: List[str], 
                         depth: int, path: List) -> Optional[List]:
        """
        回溯搜索最右推导
        :param current: 当前句型
        :param target: 目标句子
        :param depth: 当前深度
        :param path: 已走过的路径
        :return: 推导步骤列表，失败返回None
        """
        # 检查是否达到目标
        if current == target:
            return []
        
        # 检查深度限制
        if depth >= self.max_depth:
            return None
        
        # 检查是否所有符号都是终结符
        all_terminals = all(s in self.grammar.terminals for s in current)
        if all_terminals and current != target:
            return None
        
        # 检查长度
        if len(current) > len(target):
            terminal_count = sum(1 for s in current if s in self.grammar.terminals)
            if terminal_count > len(target):
                return None
        
        # 找到最右边的非终结符
        rightmost_pos = -1
        rightmost_nt = None
        for i in range(len(current) - 1, -1, -1):
            if current[i] in self.grammar.non_terminals:
                rightmost_pos = i
                rightmost_nt = current[i]
                break
        
        if rightmost_nt is None:
            # 没有非终结符了
            return None
        
        # 尝试该非终结符的所有产生式
        for production in self.grammar.productions:
            if production.left != rightmost_nt:
                continue
            
            # 应用产生式
            new_current = current[:rightmost_pos]
            if not production.is_epsilon():
                new_current.extend(production.right)
            new_current.extend(current[rightmost_pos + 1:])
            
            # 递归搜索
            result = self._search_rightmost(new_current, target, depth + 1, path + [(new_current, production)])
            
            if result is not None:
                # 找到解
                return [(new_current, production)] + result
        
        # 所有产生式都失败
        return None
