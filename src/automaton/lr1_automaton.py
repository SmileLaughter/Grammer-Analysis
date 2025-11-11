"""
LR(1) 自动机构造器
用于构造 LR(1) 项集规范族和 DFA
"""

from typing import Set, Dict, List, Tuple
from src.core.grammar import Grammar, Production
from src.automaton.lr_item import LR1Item, ItemSet
from src.core.first_follow import FirstFollowCalculator


class LR1Automaton:
    """
    LR(1) 自动机
    负责构造 LR(1) 项集规范族和状态转移图
    """
    
    def __init__(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        初始化自动机
        :param grammar: 增广文法
        :param calculator: FIRST/FOLLOW 集计算器
        """
        self.grammar = grammar
        self.calculator = calculator
        self.states: List[ItemSet] = []  # 所有状态（项集）
        self.transitions: Dict[Tuple[int, str], int] = {}  # 状态转移
        self.start_state: ItemSet = None  # 开始状态
    
    def build(self) -> bool:
        """
        构造 LR(1) 自动机
        :return: 是否构建成功
        """
        # 获取增广文法的开始产生式（S' → S）
        start_production = self.grammar.productions[0]
        
        # 构造初始项集 I1 = closure({[S' → ·S, $]})（状态从1开始编号）
        initial_item = LR1Item(start_production, 0, '$')
        self.start_state = ItemSet(state_id=1)
        self.start_state.add_item(initial_item)
        self.start_state = self.closure(self.start_state)
        
        # 使用队列进行 BFS 构造所有状态
        self.states = [self.start_state]
        state_queue = [self.start_state]
        state_set = {self.start_state}  # 用于快速查找是否已存在
        
        while state_queue:
            current_state = state_queue.pop(0)
            
            # 收集当前状态中点后的所有符号
            symbols_set = set()
            for item in current_state:
                next_sym = item.next_symbol()
                if next_sym is not None:
                    symbols_set.add(next_sym)
            
            # 根据配置决定是否排序符号
            try:
                from src.config.dfa_config import dfa_config
                if dfa_config.is_deterministic():
                    symbols = sorted(symbols_set)  # 确定性模式：按字典序排序
                else:
                    symbols = list(symbols_set)  # 非确定性模式：使用set的自然顺序
            except ImportError:
                symbols = sorted(symbols_set)  # 默认使用确定性模式
            
            # 对每个符号计算 goto
            for symbol in symbols:
                new_state = self.goto(current_state, symbol)
                
                if len(new_state) == 0:
                    continue
                
                # 检查是否已存在相同的状态
                existing_state = None
                for state in state_set:
                    if state == new_state:
                        existing_state = state
                        break
                
                if existing_state is None:
                    # 新状态，添加到列表（状态编号从1开始）
                    new_state.state_id = len(self.states) + 1
                    self.states.append(new_state)
                    state_queue.append(new_state)
                    state_set.add(new_state)
                    target_state_id = new_state.state_id
                else:
                    # 已存在的状态
                    target_state_id = existing_state.state_id
                
                # 记录转移
                self.transitions[(current_state.state_id, symbol)] = target_state_id
        
        return True
    
    def closure(self, item_set: ItemSet) -> ItemSet:
        """
        计算 LR(1) 项集的闭包
        算法：
        1. 初始时，闭包包含项集中的所有项
        2. 对于闭包中的每个项 [A → α·Bβ, a]（B 是非终结符）
           - 计算 FIRST(βa)
           - 对于每个 b ∈ FIRST(βa)，将 [B → ·γ, b] 加入闭包
        3. 重复步骤 2，直到没有新项加入
        
        :param item_set: 输入项集
        :return: 闭包后的项集
        """
        # 创建新项集作为闭包结果
        closure_set = ItemSet(state_id=item_set.state_id)
        for item in item_set:
            closure_set.add_item(item)
        
        # 使用工作列表算法
        added = True
        while added:
            added = False
            # 根据配置决定是否使用确定性顺序
            try:
                from src.config.dfa_config import dfa_config
                if dfa_config.is_deterministic():
                    current_items = closure_set._get_sorted_items()
                else:
                    current_items = list(closure_set.items)
            except ImportError:
                current_items = closure_set._get_sorted_items()
            
            for item in current_items:
                next_sym = item.next_symbol()
                
                # 如果点后面是非终结符
                if next_sym and next_sym in self.grammar.non_terminals:
                    # 计算 FIRST(βa)，其中 β 是点后面的剩余部分，a 是向前看符号
                    beta = item.right[item.dot_position + 1:]  # 点后面的剩余符号
                    beta_a = beta + [item.lookahead]  # β 后面跟向前看符号
                    
                    # 计算 FIRST(βa)
                    first_beta_a = self._compute_first_of_string(beta_a)
                    
                    # 找到该非终结符的所有产生式（按产生式索引顺序遍历）
                    for production in self.grammar.productions:
                        if production.left == next_sym:
                            # 根据配置决定是否排序前看符号
                            try:
                                from src.config.dfa_config import dfa_config
                                lookaheads = sorted(first_beta_a) if dfa_config.is_deterministic() else first_beta_a
                            except ImportError:
                                lookaheads = sorted(first_beta_a)
                            
                            # 对于 FIRST(βa) 中的每个符号，创建新项
                            for lookahead in lookaheads:
                                # 创建新项 [B → ·γ, lookahead]
                                new_item = LR1Item(production, 0, lookahead)
                                
                                # 如果这是新项，添加到闭包
                                if new_item not in closure_set.items:
                                    closure_set.add_item(new_item)
                                    added = True
        
        return closure_set
    
    def _compute_first_of_string(self, symbols: List[str]) -> Set[str]:
        """
        计算符号串的 FIRST 集
        :param symbols: 符号列表
        :return: FIRST 集
        """
        if not symbols:
            return set()
        
        result = set()
        
        for i, symbol in enumerate(symbols):
            # 如果是终结符，直接返回
            if symbol in self.grammar.terminals or symbol == '$':
                result.add(symbol)
                break
            
            # 如果是非终结符，获取其 FIRST 集
            if symbol in self.grammar.non_terminals:
                first_set = self.calculator.get_first_set(symbol)
                result.update(first_set)
                
                # 如果该非终结符不可推导出空串，停止
                if symbol not in self.calculator.nullable:
                    break
            
            # 如果到达最后一个符号且都可为空，整个串可为空
            if i == len(symbols) - 1:
                # 但在 LR(1) 中，空串不会出现在 lookahead 中
                pass
        
        return result
    
    def goto(self, item_set: ItemSet, symbol: str) -> ItemSet:
        """
        计算 GOTO 函数
        GOTO(I, X) = closure({[A → αX·β, a] | [A → α·Xβ, a] ∈ I})
        
        :param item_set: 输入项集
        :param symbol: 转移符号
        :return: 转移后的项集
        """
        # 收集所有点后面是 symbol 的项，并将点向前移动
        moved_items = ItemSet()
        
        for item in item_set:
            if item.next_symbol() == symbol:
                moved_items.add_item(item.advance())
        
        # 如果没有可移动的项，返回空集
        if len(moved_items) == 0:
            return moved_items
        
        # 计算闭包
        return self.closure(moved_items)
    
    def get_state_by_id(self, state_id: int) -> ItemSet:
        """
        根据状态 ID 获取状态
        :param state_id: 状态编号
        :return: 项集
        """
        for state in self.states:
            if state.state_id == state_id:
                return state
        return None
    
    def get_transition(self, state_id: int, symbol: str) -> int:
        """
        获取状态转移
        :param state_id: 源状态 ID
        :param symbol: 转移符号
        :return: 目标状态 ID，如果不存在则返回 None
        """
        return self.transitions.get((state_id, symbol))
    
    def print_automaton(self):
        """打印自动机信息（用于调试）"""
        print(f"\n共有 {len(self.states)} 个状态")
        print(f"共有 {len(self.transitions)} 个转移\n")
        
        for state in self.states:
            print(state)
            print()
        
        print("状态转移：")
        for (state_id, symbol), target_id in sorted(self.transitions.items()):
            print(f"  I{state_id} --{symbol}--> I{target_id}")
