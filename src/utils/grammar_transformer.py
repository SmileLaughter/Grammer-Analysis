"""
文法转换模块
自动尝试将不满足 LL(1) 条件的文法转换为 LL(1) 文法
"""

from typing import List, Set, Dict, Tuple, Optional
from src.core.grammar import Grammar, Production
from src.core.first_follow import FirstFollowCalculator
from copy import deepcopy


class GrammarTransformer:
    """文法转换器"""
    
    def __init__(self, grammar: Grammar):
        """
        初始化转换器
        :param grammar: 原始文法
        """
        self.original_grammar = grammar
        self.transformed_grammar = None
        self.transformations = []  # 记录转换步骤
        self.new_non_terminal_counter = 0  # 用于生成新的非终结符
    
    def transform_to_ll1(self) -> Tuple[Grammar, bool, List[str]]:
        """
        尝试将文法转换为 LL(1) 文法
        :return: (转换后的文法, 是否成功, 转换步骤列表)
        """
        # 复制原文法
        self.transformed_grammar = self._copy_grammar(self.original_grammar)
        self.transformations = []
        
        # 最多尝试 10 轮转换
        max_iterations = 10
        for iteration in range(max_iterations):
            # 计算集合
            calculator = FirstFollowCalculator(self.transformed_grammar)
            calculator.calculate_all()
            
            # 检查是否需要转换
            conflicts = self._find_conflicts(calculator)
            
            if not conflicts:
                # 没有冲突，转换成功
                return self.transformed_grammar, True, self.transformations
            
            # 尝试解决冲突
            transformed = False
            
            for conflict in conflicts:
                if self._resolve_conflict(conflict, calculator):
                    transformed = True
                    break  # 每次只解决一个冲突，然后重新计算
            
            if not transformed:
                # 无法解决任何冲突
                return self.transformed_grammar, False, self.transformations
        
        # 超过最大迭代次数
        return self.transformed_grammar, False, self.transformations
    
    def _copy_grammar(self, grammar: Grammar) -> Grammar:
        """
        复制文法
        :param grammar: 原文法
        :return: 复制的文法
        """
        new_grammar = Grammar()
        new_grammar.start_symbol = grammar.start_symbol
        new_grammar.non_terminals = grammar.non_terminals.copy()
        new_grammar.terminals = grammar.terminals.copy()
        
        for prod in grammar.productions:
            new_grammar.add_production(prod.left, prod.right.copy())
        
        return new_grammar
    
    def _find_conflicts(self, calculator: FirstFollowCalculator) -> List[Dict]:
        """
        查找所有冲突
        :param calculator: FIRST/FOLLOW 计算器
        :return: 冲突列表
        """
        conflicts = []
        
        # 先检查左递归（优先级最高）
        for nt in self.transformed_grammar.non_terminals:
            if self._has_left_recursion(nt):
                conflicts.append({
                    'type': 'LEFT_RECURSION',
                    'non_terminal': nt
                })
        
        # 如果有左递归，只返回左递归冲突（优先处理）
        if conflicts:
            return conflicts
        
        # 遍历每个非终结符，查找其他冲突
        for nt in self.transformed_grammar.non_terminals:
            prods = self.transformed_grammar.get_productions_for(nt)
            
            if len(prods) < 2:
                continue
            
            # 检查每对产生式
            for i in range(len(prods)):
                for j in range(i + 1, len(prods)):
                    conflict = self._check_conflict(prods[i], prods[j], calculator)
                    if conflict:
                        conflicts.append(conflict)
        
        return conflicts
    
    def _has_left_recursion(self, non_terminal: str) -> bool:
        """
        检查非终结符是否有直接左递归
        :param non_terminal: 非终结符
        :return: 是否有左递归
        """
        prods = self.transformed_grammar.get_productions_for(non_terminal)
        
        for prod in prods:
            # 检查右部第一个符号是否是自身（直接左递归）
            if prod.right and prod.right[0] == non_terminal:
                return True
        
        return False
    
    def _check_conflict(self, prod1: Production, prod2: Production, 
                       calculator: FirstFollowCalculator) -> Optional[Dict]:
        """
        检查两个产生式是否有冲突
        :param prod1: 产生式1
        :param prod2: 产生式2
        :param calculator: FIRST/FOLLOW 计算器
        :return: 冲突信息字典，如果没有冲突则返回 None
        """
        first1 = calculator.get_production_first_set(prod1)
        first2 = calculator.get_production_first_set(prod2)
        
        # 检查 FIRST 集冲突
        first_intersection = first1 & first2
        if first_intersection:
            return {
                'type': 'FIRST_FIRST',
                'non_terminal': prod1.left,
                'prod1': prod1,
                'prod2': prod2,
                'first1': first1,
                'first2': first2,
                'intersection': first_intersection
            }
        
        # 检查 FIRST-FOLLOW 冲突
        nullable1 = self._is_nullable(prod1, calculator)
        nullable2 = self._is_nullable(prod2, calculator)
        follow_set = calculator.get_follow_set(prod1.left)
        
        if nullable1:
            follow_intersection = first2 & follow_set
            if follow_intersection:
                return {
                    'type': 'FIRST_FOLLOW',
                    'non_terminal': prod1.left,
                    'prod1': prod1,  # nullable
                    'prod2': prod2,
                    'follow': follow_set,
                    'first2': first2,
                    'intersection': follow_intersection
                }
        
        if nullable2:
            follow_intersection = first1 & follow_set
            if follow_intersection:
                return {
                    'type': 'FIRST_FOLLOW',
                    'non_terminal': prod2.left,
                    'prod1': prod2,  # nullable
                    'prod2': prod1,
                    'follow': follow_set,
                    'first2': first1,
                    'intersection': follow_intersection
                }
        
        return None
    
    def _is_nullable(self, prod: Production, calculator: FirstFollowCalculator) -> bool:
        """
        判断产生式是否可推导出空串
        :param prod: 产生式
        :param calculator: FIRST/FOLLOW 计算器
        :return: 是否可推导出空串
        """
        if prod.is_epsilon():
            return True
        
        nullable_set = calculator.get_nullable_set()
        return all(s in nullable_set for s in prod.right)
    
    def _resolve_conflict(self, conflict: Dict, calculator: FirstFollowCalculator) -> bool:
        """
        尝试解决一个冲突
        :param conflict: 冲突信息
        :param calculator: FIRST/FOLLOW 计算器
        :return: 是否成功解决
        """
        if conflict['type'] == 'LEFT_RECURSION':
            # 左递归：消除左递归
            return self._eliminate_left_recursion(conflict)
        elif conflict['type'] == 'FIRST_FIRST':
            # FIRST 集冲突：提取左公因子
            return self._extract_left_factor(conflict)
        elif conflict['type'] == 'FIRST_FOLLOW':
            # FIRST-FOLLOW 冲突
            return self._resolve_first_follow_conflict(conflict, calculator)
        
        return False
    
    def _eliminate_left_recursion(self, conflict: Dict) -> bool:
        """
        消除直接左递归
        A -> A α1 | A α2 | ... | β1 | β2 | ...
        转换为:
        A -> β1 A' | β2 A' | ...
        A' -> α1 A' | α2 A' | ... | ε
        
        :param conflict: 冲突信息
        :return: 是否成功
        """
        nt = conflict['non_terminal']
        prods = self.transformed_grammar.get_productions_for(nt)
        
        # 将产生式分为两类
        recursive_prods = []  # A -> A α 形式
        non_recursive_prods = []  # A -> β 形式
        
        for prod in prods:
            if prod.right and prod.right[0] == nt:
                # 左递归产生式
                recursive_prods.append(prod)
            else:
                # 非左递归产生式
                non_recursive_prods.append(prod)
        
        if not recursive_prods or not non_recursive_prods:
            # 没有找到左递归或没有非递归产生式
            return False
        
        # 生成新的非终结符 A'
        new_nt = self._generate_new_non_terminal(nt)
        
        # 移除所有旧的产生式
        self.transformed_grammar.productions = [
            p for p in self.transformed_grammar.productions if p.left != nt
        ]
        
        # 添加新产生式：A -> β1 A' | β2 A' | ...
        for prod in non_recursive_prods:
            new_right = prod.right + [new_nt]
            self.transformed_grammar.add_production(nt, new_right)
        
        # 添加新产生式：A' -> α1 A' | α2 A' | ... | ε
        for prod in recursive_prods:
            # 去掉左部的 A，得到 α
            alpha = prod.right[1:]
            new_right = alpha + [new_nt]
            self.transformed_grammar.add_production(new_nt, new_right)
        
        # 添加 epsilon 产生式
        self.transformed_grammar.add_production(new_nt, [])
        
        # 记录转换
        old_prods_str = ' | '.join(str(p) for p in prods)
        new_prods = self.transformed_grammar.get_productions_for(nt) + \
                   self.transformed_grammar.get_productions_for(new_nt)
        new_prods_str = ' | '.join(str(p) for p in new_prods)
        
        self.transformations.append(
            f"消除左递归: {nt}\n  原产生式: {old_prods_str}\n  新产生式: {new_prods_str}"
        )
        
        return True
    
    def _extract_left_factor(self, conflict: Dict) -> bool:
        """
        提取左公因子
        :param conflict: 冲突信息
        :return: 是否成功
        """
        prod1 = conflict['prod1']
        prod2 = conflict['prod2']
        
        # 找到公共前缀
        common_prefix = self._find_common_prefix(prod1.right, prod2.right)
        
        if not common_prefix:
            # 没有公共前缀，无法提取左公因子
            return False
        
        # 生成新的非终结符
        new_nt = self._generate_new_non_terminal(prod1.left)
        
        # 移除旧的产生式
        self.transformed_grammar.productions = [
            p for p in self.transformed_grammar.productions 
            if p != prod1 and p != prod2
        ]
        
        # 添加新产生式：A -> prefix A'
        new_prod_right = common_prefix + [new_nt]
        self.transformed_grammar.add_production(prod1.left, new_prod_right)
        
        # 添加新产生式：A' -> suffix1 | suffix2
        suffix1 = prod1.right[len(common_prefix):]
        suffix2 = prod2.right[len(common_prefix):]
        
        self.transformed_grammar.add_production(new_nt, suffix1 if suffix1 else [])
        self.transformed_grammar.add_production(new_nt, suffix2 if suffix2 else [])
        
        # 记录转换
        self.transformations.append(
            f"提取左公因子: {prod1} 和 {prod2} -> "
            f"{prod1.left} → {' '.join(new_prod_right)}, "
            f"{new_nt} → {' '.join(suffix1) if suffix1 else 'ε'} | {' '.join(suffix2) if suffix2 else 'ε'}"
        )
        
        return True
    
    def _resolve_first_follow_conflict(self, conflict: Dict, 
                                       calculator: FirstFollowCalculator) -> bool:
        """
        解决 FIRST-FOLLOW 冲突
        :param conflict: 冲突信息
        :param calculator: FIRST/FOLLOW 计算器
        :return: 是否成功
        """
        prod1 = conflict['prod1']  # nullable 产生式
        prod2 = conflict['prod2']
        
        # 检查是否两个都是 epsilon 产生式
        if prod1.is_epsilon() and prod2.is_epsilon():
            # 删除其中一个 epsilon 产生式
            self.transformed_grammar.productions.remove(prod2)
            self.transformations.append(
                f"删除重复的 epsilon 产生式: {prod2}"
            )
            return True
        
        # 如果 prod1 是 epsilon 产生式，尝试展开 prod2
        if prod1.is_epsilon():
            # 这种情况比较复杂，暂时返回 False
            return False
        
        # 尝试提取左公因子或其他转换
        return False
    
    def _find_common_prefix(self, right1: List[str], right2: List[str]) -> List[str]:
        """
        找到两个产生式右部的公共前缀
        :param right1: 产生式1的右部
        :param right2: 产生式2的右部
        :return: 公共前缀
        """
        common = []
        for i in range(min(len(right1), len(right2))):
            if right1[i] == right2[i]:
                common.append(right1[i])
            else:
                break
        return common
    
    def _generate_new_non_terminal(self, base: str) -> str:
        """
        生成新的非终结符
        :param base: 基础非终结符
        :return: 新的非终结符
        """
        # 使用 A' 格式
        self.new_non_terminal_counter += 1
        return f"{base}'"
