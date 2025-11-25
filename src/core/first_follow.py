"""
FIRST集、FOLLOW集、NULLABLE集计算模块
"""

from typing import Set, Dict, List
from src.core.grammar import Grammar, Production
from collections import defaultdict


class FirstFollowCalculator:
    """FIRST集和FOLLOW集计算器"""
    
    def __init__(self, grammar: Grammar, include_dollar: bool = True):
        """
        初始化计算器
        :param grammar: 文法对象
        :param include_dollar: 是否在FOLLOW集中包含$符号
                               True: 用于LR系列算法（需要处理增广文法）
                               False: 用于LL(1)算法（不需要$）
        """
        self.grammar = grammar
        self.include_dollar = include_dollar
        
        # NULLABLE集：可以推导出epsilon的非终结符集合
        self.nullable: Set[str] = set()
        
        # FIRST集：每个非终结符的FIRST集
        self.first: Dict[str, Set[str]] = defaultdict(set)
        
        # FOLLOW集：每个非终结符的FOLLOW集
        self.follow: Dict[str, Set[str]] = defaultdict(set)
        
        # 产生式的FIRST集
        self.production_first: Dict[Production, Set[str]] = {}
    
    def calculate_all(self):
        """计算所有集合"""
        # 计算顺序：NULLABLE -> FIRST -> FOLLOW -> 产生式FIRST
        self._calculate_nullable()
        self._calculate_first()
        self._calculate_follow()
        self._calculate_production_first()
    
    def _calculate_nullable(self):
        """
        计算NULLABLE集
        一个非终结符A是nullable的，当且仅当：
        1. 存在产生式 A -> ε
        2. 或存在产生式 A -> B1 B2 ... Bn，其中所有Bi都是nullable的
        """
        # 初始化：找到所有epsilon产生式的左部
        for prod in self.grammar.productions:
            if prod.is_epsilon():
                self.nullable.add(prod.left)
        
        # 不断迭代直到不再有新的nullable非终结符
        changed = True
        while changed:
            changed = False
            
            # 遍历所有产生式
            for prod in self.grammar.productions:
                # 如果左部已经是nullable，跳过
                if prod.left in self.nullable:
                    continue
                
                # 检查右部是否全部nullable
                if prod.is_epsilon():
                    continue
                
                all_nullable = True
                for symbol in prod.right:
                    # 如果是终结符，则不是nullable
                    if symbol in self.grammar.terminals:
                        all_nullable = False
                        break
                    # 如果是非终结符但不是nullable，则不满足条件
                    if symbol in self.grammar.non_terminals and symbol not in self.nullable:
                        all_nullable = False
                        break
                
                # 如果右部全部nullable，则左部也是nullable
                if all_nullable:
                    self.nullable.add(prod.left)
                    changed = True
    
    def _calculate_first(self):
        """
        计算每个非终结符的FIRST集
        FIRST(A) 包含所有可以从A推导出的串的首终结符
        """
        # 初始化：终结符的FIRST集是它自己
        for terminal in self.grammar.terminals:
            self.first[terminal] = {terminal}
        
        # 初始化：所有非终结符的FIRST集为空
        for non_terminal in self.grammar.non_terminals:
            self.first[non_terminal] = set()
        
        # 不断迭代直到不再有变化
        changed = True
        while changed:
            changed = False
            
            # 遍历所有产生式
            for prod in self.grammar.productions:
                # 获取产生式右部的FIRST集
                first_set = self._get_first_of_string(prod.right)
                
                # 将新的终结符加入到左部非终结符的FIRST集中
                old_size = len(self.first[prod.left])
                self.first[prod.left].update(first_set)
                
                # 如果有新增，标记changed为True
                if len(self.first[prod.left]) > old_size:
                    changed = True
    
    def _get_first_of_string(self, symbols: List[str]) -> Set[str]:
        """
        计算符号串的FIRST集
        :param symbols: 符号列表
        :return: FIRST集
        """
        result = set()
        
        # 如果符号串为空（epsilon），返回空集
        if not symbols:
            return result
        
        # 遍历符号串
        for symbol in symbols:
            # 如果是终结符，加入结果并停止
            if symbol in self.grammar.terminals:
                result.add(symbol)
                break
            
            # 如果是非终结符，加入其FIRST集（不包括epsilon）
            if symbol in self.grammar.non_terminals:
                result.update(self.first[symbol])
            
            # 如果当前符号不是nullable，停止
            if symbol not in self.nullable:
                break
        
        return result
    
    def _calculate_follow(self):
        """
        计算每个非终结符的FOLLOW集
        FOLLOW(A) 包含所有可能紧跟在A后面的终结符
        """
        # 初始化：所有非终结符的FOLLOW集为空
        for non_terminal in self.grammar.non_terminals:
            self.follow[non_terminal] = set()
        
        # 文法初始符号的FOLLOW集初始化为{$}
        self.follow[self.grammar.start_symbol].add('$')
        
        # 不断迭代直到不再有变化
        changed = True
        while changed:
            changed = False
            
            # 遍历所有产生式
            for prod in self.grammar.productions:
                # 遍历产生式右部的每个符号
                for i, symbol in enumerate(prod.right):
                    # 只处理非终结符
                    if symbol not in self.grammar.non_terminals:
                        continue
                    
                    # 获取当前符号后面的串
                    rest = prod.right[i + 1:]
                    
                    # 计算rest的FIRST集
                    first_of_rest = self._get_first_of_string(rest)
                    
                    # 将first_of_rest加入到symbol的FOLLOW集
                    old_size = len(self.follow[symbol])
                    self.follow[symbol].update(first_of_rest)
                    
                    # 如果rest可以推导出epsilon（即rest为空或rest中所有符号都nullable）
                    # 则将prod.left的FOLLOW集加入到symbol的FOLLOW集
                    rest_is_nullable = all(s in self.nullable for s in rest)
                    if not rest or rest_is_nullable:
                        self.follow[symbol].update(self.follow[prod.left])
                    
                    # 检查是否有变化
                    if len(self.follow[symbol]) > old_size:
                        changed = True
    
    def _calculate_production_first(self):
        """
        计算每个产生式的FIRST集
        产生式 A -> α 的FIRST集就是 FIRST(α)
        """
        for prod in self.grammar.productions:
            self.production_first[prod] = self._get_first_of_string(prod.right)
    
    def get_nullable_set(self) -> Set[str]:
        """获取NULLABLE集"""
        return self.nullable.copy()
    
    def get_first_set(self, symbol: str) -> Set[str]:
        """
        获取符号的FIRST集
        :param symbol: 终结符或非终结符
        :return: FIRST集
        """
        return self.first.get(symbol, set()).copy()
    
    def get_follow_set(self, non_terminal: str) -> Set[str]:
        """
        获取非终结符的FOLLOW集
        :param non_terminal: 非终结符
        :return: FOLLOW集（根据include_dollar参数决定是否包含$）
        """
        return self.follow.get(non_terminal, set()).copy()
    
    def get_follow_set_for_display(self, non_terminal: str) -> Set[str]:
        """
        获取非终结符的FOLLOW集用于显示
        :param non_terminal: 非终结符
        :return: FOLLOW集
        """
        follow_set = self.follow.get(non_terminal, set()).copy()
        return follow_set
    
    def get_production_first_set(self, production: Production) -> Set[str]:
        """
        获取产生式的FIRST集（仅计算右部的FIRST集）
        :param production: 产生式
        :return: FIRST集
        """
        return self.production_first.get(production, set()).copy()
    
    def get_select_set(self, production: Production) -> Set[str]:
        """
        获取产生式的SELECT集（用于LL(1)分析）
        SELECT(A → α) = 
          - 如果 ε ∉ FIRST(α)，则 SELECT(A → α) = FIRST(α)
          - 如果 ε ∈ FIRST(α)，则 SELECT(A → α) = (FIRST(α) - {ε}) ∪ FOLLOW(A)
        
        :param production: 产生式
        :return: SELECT集
        """
        first_set = self.get_production_first_set(production).copy()
        
        # 检查右部是否能推导出epsilon
        # 方法1: 如果FIRST集包含ε
        # 方法2: 如果右部是单个ε
        # 方法3: 如果右部所有符号都是nullable的
        can_derive_epsilon = False
        
        if 'ε' in first_set:
            can_derive_epsilon = True
        elif len(production.right) == 1 and production.right[0] == 'ε':
            can_derive_epsilon = True
        elif len(production.right) == 0:
            can_derive_epsilon = True
        else:
            # 检查右部所有符号是否都是nullable
            all_nullable = all(
                symbol in self.nullable 
                for symbol in production.right 
                if symbol in self.grammar.non_terminals
            )
            # 还要确保没有终结符
            has_terminal = any(
                symbol in self.grammar.terminals
                for symbol in production.right
            )
            if all_nullable and not has_terminal:
                can_derive_epsilon = True
        
        if can_derive_epsilon:
            # SELECT = (FIRST - {ε}) ∪ FOLLOW(左部)
            first_set.discard('ε')
            # 获取FOLLOW集
            follow_set = self.follow.get(production.left, set()).copy()
            # 如果不包含$，需要移除（用于LL(1)分析表构造）
            if not self.include_dollar:
                follow_set.discard('$')
            first_set.update(follow_set)
            first_set.update(follow_set)
        
        return first_set
