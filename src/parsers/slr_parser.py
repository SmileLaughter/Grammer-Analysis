"""
SLR 语法分析器
SLR 是 LR(0) 的改进版本，使用 FOLLOW 集来减少冲突
"""

from typing import List, Tuple, Dict
from src.core.grammar import Grammar
from src.parsers.lr0_parser import LR0Parser
from src.core.first_follow import FirstFollowCalculator
from src.automaton.lr_item import LRItem


class SLRParser(LR0Parser):
    """
    SLR 语法分析器
    继承自 LR(0)，主要区别在于归约动作的添加
    """
    
    def __init__(self, grammar: Grammar):
        """
        初始化 SLR 分析器
        :param grammar: 原始文法
        """
        super().__init__(grammar)
        self.calculator = None  # FIRST/FOLLOW 集计算器
    
    def get_name(self) -> str:
        """获取分析器名称"""
        return "SLR"
    
    def build(self) -> bool:
        """
        构建 SLR 分析表
        :return: 是否构建成功（即使有冲突也返回 True，允许显示冲突信息）
        """
        # 步骤1：构造增广文法
        self.augmented_grammar = self._augment_grammar()
        
        # 步骤2：计算原始文法的 FOLLOW 集
        # 注意：FOLLOW 集基于原始文法计算，不是增广文法
        self.calculator = FirstFollowCalculator(self.grammar)
        self.calculator.calculate_all()
        
        # 步骤3：构造 LR(0) 自动机
        from src.automaton.lr0_automaton import LR0Automaton
        self.automaton = LR0Automaton(self.augmented_grammar)
        self.automaton.build()
        
        # 步骤4：构造 SLR 分析表（与 LR(0) 不同）
        self._build_slr_parsing_table()
        
        # 即使有冲突也返回 True，这样可以显示分析表和冲突信息
        return True
    
    def _build_slr_parsing_table(self):
        """
        构造 SLR 分析表
        与 LR(0) 的区别：归约动作只在 FOLLOW 集中的符号上添加
        """
        self.action_table.clear()
        self.goto_table.clear()
        self.conflicts.clear()
        self.has_conflicts = False
        
        # 遍历所有状态
        for state in self.automaton.states:
            state_id = state.state_id
            
            # 处理状态中的每一项
            for item in state:
                if item.is_reducible():
                    # 归约项（使用 SLR 规则）
                    self._add_slr_reduce_action(state_id, item)
                else:
                    # 移进项
                    next_sym = item.next_symbol()
                    if next_sym in self.augmented_grammar.terminals:
                        # 终结符：添加移进动作
                        self._add_shift_action(state_id, next_sym)
                    elif next_sym in self.augmented_grammar.non_terminals:
                        # 非终结符：添加 GOTO
                        self._add_goto_action(state_id, next_sym)
            
            # 检查是否是接受状态
            self._check_accept_state(state_id, state)
    
    def _add_slr_reduce_action(self, state_id: int, item: LRItem):
        """
        添加 SLR 归约动作
        SLR 规则：只在 FOLLOW(A) 中的符号上添加归约动作
        
        :param state_id: 状态编号
        :param item: 归约项 A → α·
        """
        # 如果是增广产生式 S' → S·，不添加归约（由接受状态处理）
        if item.production.index == 0:
            return
        
        # 获取产生式左部的 FOLLOW 集
        left_symbol = item.production.left
        follow_set = self.calculator.get_follow_set(left_symbol)
        
        # 只在 FOLLOW 集中的符号上添加归约动作
        for terminal in follow_set:
            key = (state_id, terminal)
            action = (self.REDUCE, item.production.index)
            
            # 检查是否已有动作
            if key in self.action_table:
                # 检查是否已存在相同的动作
                if action not in self.action_table[key]:
                    # 有冲突，添加到列表
                    self.has_conflicts = True
                    existing_first = self.action_table[key][0]
                    
                    # 判断冲突类型
                    existing_type = existing_first[0]
                    if existing_type == self.SHIFT:
                        conflict_type = "移进-归约冲突"
                    elif existing_type == self.REDUCE:
                        conflict_type = "归约-归约冲突"
                    else:
                        conflict_type = "冲突"
                    
                    conflict_msg = f"{conflict_type}: 状态 {state_id} 在符号 '{terminal}' 上，{self._format_action(existing_first)} 与 {self._format_action(action)}"
                    self.conflicts.append(conflict_msg)
                    
                    # 将新动作添加到列表
                    self.action_table[key].append(action)
            else:
                # 第一个动作，创建列表
                self.action_table[key] = [action]
    
    def print_table(self):
        """打印 SLR 分析表"""
        from rich.console import Console
        from rich.table import Table
        from rich import box
        
        console = Console()
        
        # 收集所有终结符和非终结符
        terminals = sorted(self.augmented_grammar.terminals)
        if '$' not in terminals:
            terminals.append('$')
        non_terminals = sorted([nt for nt in self.augmented_grammar.non_terminals 
                               if nt != self.augmented_grammar.start_symbol])
        
        # 创建表格标题
        title = "SLR 分析表"
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
            console.print("  - [yellow]该文法不是 SLR 文法，建议尝试更强的 LR(1) 或 LALR 分析算法[/yellow]")
