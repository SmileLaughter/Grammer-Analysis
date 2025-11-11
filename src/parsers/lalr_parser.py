"""
LALR(1) 语法分析器
通过合并 LR(1) 中具有相同核心的状态来减少状态数量
"""

from typing import List, Tuple, Dict, Set
from src.core.grammar import Grammar
from src.parsers.lr1_parser import LR1Parser
from src.automaton.lr1_automaton import LR1Automaton
from src.automaton.lr_item import LR1Item
from src.core.first_follow import FirstFollowCalculator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class ItemSet:
    """项集类，用于表示 LALR(1) 的状态"""
    
    def __init__(self, state_id: int, items: Set[LR1Item] = None):
        """
        初始化项集
        :param state_id: 状态编号
        :param items: LR(1) 项的集合
        """
        self.state_id = state_id
        self.items = items if items else set()
    
    def __iter__(self):
        return iter(self.items)
    
    def __len__(self):
        return len(self.items)
    
    def add(self, item: LR1Item):
        """添加项"""
        self.items.add(item)
    
    def get_core(self) -> Set[Tuple]:
        """
        获取项集的核心（不包含向前看符号）
        :return: 核心的集合，元素为 (production_index, dot_position)
        """
        return {(item.production.index, item.dot_position) for item in self.items}
    
    def merge(self, other_items: Set[LR1Item]):
        """
        合并另一个项集的项（合并向前看符号）
        :param other_items: 另一个项集的项
        """
        # 按照 (production, dot_position) 分组当前项
        current_items_map = {}
        for item in self.items:
            key = (item.production.index, item.dot_position)
            if key not in current_items_map:
                current_items_map[key] = item
            else:
                # 理论上不应该发生，因为同一核心应该只有一个项
                pass
        
        # 合并新项
        for new_item in other_items:
            key = (new_item.production.index, new_item.dot_position)
            if key in current_items_map:
                # 找到同核心的项，创建新项合并向前看符号
                existing_item = current_items_map[key]
                # 移除旧项
                self.items.discard(existing_item)
                # 创建新项，合并向前看符号（这里简化处理，实际上应该合并）
                # 由于 LR1Item 的 lookahead 是单个符号，我们需要重新设计
                # 这里我们保持原有的项，但在构建时需要特殊处理
                self.items.add(existing_item)
                self.items.add(new_item)
            else:
                # 新的核心项
                self.items.add(new_item)
                current_items_map[key] = new_item


class LALRAutomaton:
    """LALR(1) 自动机"""
    
    def __init__(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        初始化 LALR(1) 自动机
        :param grammar: 增广文法
        :param calculator: FIRST/FOLLOW 集计算器
        """
        self.grammar = grammar
        self.calculator = calculator
        self.states = []  # LALR(1) 状态列表
        self.transitions = {}  # 状态转移 {(state_id, symbol): target_state_id}
        self.lr1_automaton = None  # LR(1) 自动机
    
    def build(self):
        """构造 LALR(1) 自动机（通过合并 LR(1) 同核心状态）"""
        # 步骤1：构造 LR(1) 自动机
        self.lr1_automaton = LR1Automaton(self.grammar, self.calculator)
        self.lr1_automaton.build()
        
        # 步骤2：按核心分组 LR(1) 状态
        core_groups = self._group_by_core()
        
        # 步骤3：合并同核心的状态
        self._merge_states(core_groups)
    
    def _group_by_core(self) -> Dict[frozenset, List[int]]:
        """
        按核心分组 LR(1) 状态
        :return: {core: [state_id1, state_id2, ...]}
        """
        core_groups = {}
        
        for state in self.lr1_automaton.states:
            # 计算核心
            core = frozenset((item.production.index, item.dot_position) 
                           for item in state.items)
            
            if core not in core_groups:
                core_groups[core] = []
            core_groups[core].append(state.state_id)
        
        return core_groups
    
    def _merge_states(self, core_groups: Dict[frozenset, List[int]]):
        """
        合并同核心的状态
        :param core_groups: {core: [state_id1, state_id2, ...]}
        """
        # 创建状态编号映射 {lr1_state_id: lalr_state_id}
        state_mapping = {}
        lalr_state_id = 1  # 从1开始编号
        
        # 根据配置决定是否使用确定性顺序
        try:
            from src.config.dfa_config import dfa_config
            if dfa_config.is_deterministic():
                # 按照最小的lr1_state_id排序，确保每次合并顺序一致
                sorted_cores = sorted(core_groups.items(), key=lambda x: min(x[1]))
            else:
                sorted_cores = list(core_groups.items())
        except ImportError:
            sorted_cores = sorted(core_groups.items(), key=lambda x: min(x[1]))
        
        for core, lr1_state_ids in sorted_cores:
            # 合并这些状态的项（向前看符号求并集）
            merged_items = set()
            
            for lr1_id in lr1_state_ids:
                # 通过state_id查找对应的state对象
                lr1_state = None
                for state in self.lr1_automaton.states:
                    if state.state_id == lr1_id:
                        lr1_state = state
                        break
                
                if lr1_state is None:
                    continue
                
                # 将所有项添加到合并集合
                for item in lr1_state.items:
                    merged_items.add(item)
            
            # 创建 LALR 状态
            lalr_state = ItemSet(lalr_state_id, merged_items)
            self.states.append(lalr_state)
            
            # 记录映射
            for lr1_id in lr1_state_ids:
                state_mapping[lr1_id] = lalr_state_id
            
            lalr_state_id += 1
        
        # 构建 LALR 转移关系
        self._build_transitions(state_mapping)
    
    def _build_transitions(self, state_mapping: Dict[int, int]):
        """
        根据 LR(1) 转移构建 LALR(1) 转移
        :param state_mapping: {lr1_state_id: lalr_state_id}
        """
        # 遍历 LR(1) 的转移
        for (lr1_from, symbol), lr1_to in self.lr1_automaton.transitions.items():
            # 映射到 LALR 状态
            lalr_from = state_mapping[lr1_from]
            lalr_to = state_mapping[lr1_to]
            
            # 添加 LALR 转移（如果已存在则覆盖，但应该是一致的）
            self.transitions[(lalr_from, symbol)] = lalr_to
    
    def get_transition(self, state_id: int, symbol: str) -> int:
        """
        获取状态转移
        :param state_id: 源状态 ID
        :param symbol: 输入符号
        :return: 目标状态 ID，如果不存在则返回 -1
        """
        return self.transitions.get((state_id, symbol), -1)


class LALRParser(LR1Parser):
    """LALR(1) 语法分析器"""
    
    def __init__(self, grammar: Grammar):
        """
        初始化 LALR(1) 分析器
        :param grammar: 原始文法
        """
        super().__init__(grammar)
    
    def get_name(self) -> str:
        """获取分析器名称"""
        return "LALR(1)"
    
    def build(self) -> bool:
        """
        构建 LALR(1) 分析表
        :return: 是否构建成功
        """
        # 步骤1：构造增广文法
        self.augmented_grammar = self._augment_grammar()
        
        # 步骤2：计算原始文法的 FIRST/FOLLOW 集
        self.calculator = FirstFollowCalculator(self.grammar)
        self.calculator.calculate_all()
        
        # 步骤3：构造 LALR(1) 自动机
        self.automaton = LALRAutomaton(self.augmented_grammar, self.calculator)
        self.automaton.build()
        
        # 步骤4：构造 LALR(1) 分析表
        self._build_lr1_parsing_table()
        
        return True
    
    def print_table(self):
        """打印 LALR(1) 分析表"""
        console = Console()
        
        # 收集所有终结符和非终结符
        terminals = sorted(self.augmented_grammar.terminals)
        if '$' not in terminals:
            terminals.append('$')
        non_terminals = sorted([nt for nt in self.augmented_grammar.non_terminals 
                               if nt != self.augmented_grammar.start_symbol])
        
        # 创建表格标题
        title = "LALR(1) 分析表"
        if self.has_conflicts:
            title += " [red](有冲突)[/red]"
        
        # 创建表格
        table = Table(title=title, box=box.HEAVY_HEAD, show_lines=True)
        
        # 添加列
        table.add_column("状态", justify="center", style="cyan", no_wrap=True)
        
        # ACTION 列
        for terminal in terminals:
            table.add_column(terminal, justify="center", style="yellow")
        
        # GOTO 列
        for non_terminal in non_terminals:
            table.add_column(non_terminal, justify="center", style="green")
        
        # 填充表格
        for state in self.automaton.states:
            state_id = state.state_id
            row = [str(state_id)]
            
            # ACTION 部分
            for terminal in terminals:
                key = (state_id, terminal)
                if key in self.action_table:
                    actions = self.action_table[key]
                    # 格式化所有动作
                    action_strs = []
                    for action_type, value in actions:
                        if action_type == self.SHIFT:
                            action_strs.append(f"s{value}")
                        elif action_type == self.REDUCE:
                            action_strs.append(f"r{value}")
                        elif action_type == self.ACCEPT:
                            action_strs.append("acc")
                    
                    # 如果有多个动作（冲突），用 / 分隔并标红
                    if len(action_strs) > 1:
                        cell = "[red]" + "/".join(action_strs) + "[/red]"
                    else:
                        cell = action_strs[0] if action_strs else ""
                else:
                    cell = ""
                row.append(cell)
            
            # GOTO 部分
            for non_terminal in non_terminals:
                key = (state_id, non_terminal)
                if key in self.goto_table:
                    # 在状态编号前加上 'g' 前缀，表示 goto
                    cell = f"g{self.goto_table[key]}"
                else:
                    cell = ""
                row.append(cell)
            
            table.add_row(*row)
        
        console.print(table)
        
        # 如果有冲突，打印冲突信息
        if self.has_conflicts:
            console.print(f"\n[bold red]! 检测到 {len(self.conflicts)} 个冲突：[/bold red]")
            for i, conflict in enumerate(self.conflicts, 1):
                console.print(f"  [red]{i}. {conflict}[/red]")
            
            console.print("\n[yellow]说明：[/yellow]")
            console.print("  - [yellow]移进-归约冲突[/yellow]：无法确定是移进符号还是归约")
            console.print("  - [yellow]归约-归约冲突[/yellow]：无法确定使用哪个产生式归约")
            console.print("  - [yellow]该文法不是 LALR(1) 文法[/yellow]")
    
    def print_dfa(self):
        """打印 DFA（LALR(1) 项集规范族）"""
        console = Console()
        
        console.print("\n[bold cyan]LALR(1) 项集规范族（DFA）[/bold cyan]")
        console.print(f"[dim]状态数：{len(self.automaton.states)} (LR(1) 状态数：{len(self.automaton.lr1_automaton.states)})[/dim]\n")
        
        for state in self.automaton.states:
            # 将相同核心（产生式和点位置相同）的项合并，收集它们的前看符号
            from collections import defaultdict
            core_to_lookaheads = defaultdict(set)
            
            for item in state.items:
                # 核心是 (产生式, 点位置)
                core = (item.production, item.dot_position)
                # LALR 项的 lookahead 可能是集合
                if isinstance(item.lookahead, set):
                    core_to_lookaheads[core].update(item.lookahead)
                else:
                    core_to_lookaheads[core].add(item.lookahead)
            
            # 构造合并后的项字符串
            merged_items = []
            for (production, dot_pos), lookaheads in core_to_lookaheads.items():
                # 构造右部，在适当位置插入点
                right_with_dot = list(production.right)
                right_with_dot.insert(dot_pos, '·')
                right_str = ' '.join(right_with_dot) if right_with_dot else '·'
                
                # 前看符号排序后用逗号分隔
                lookahead_str = ', '.join(sorted(lookaheads))
                
                item_str = f"[{production.left} → {right_str}, {lookahead_str}]"
                merged_items.append((production.index, dot_pos, item_str))
            
            # 排序后输出
            items_str = '\n'.join(item_str for _, _, item_str in sorted(merged_items))
            
            panel = Panel(
                items_str,
                title=f"[bold]状态 I{state.state_id}[/bold]",
                border_style="cyan",
                expand=False
            )
            console.print(panel)
        
        # 打印状态转移
        console.print("\n[bold cyan]状态转移：[/bold cyan]")
        for (state_id, symbol), target_id in sorted(self.automaton.transitions.items()):
            console.print(f"  I{state_id} --[yellow]{symbol}[/yellow]--> I{target_id}")
