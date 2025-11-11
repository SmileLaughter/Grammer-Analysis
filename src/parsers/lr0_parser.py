"""
LR(0) 语法分析器
"""

from typing import List, Tuple, Dict, Set
from src.core.grammar import Grammar, Production
from src.core.parser_interface import ParserInterface
from src.automaton.lr_item import LRItem, ItemSet
from src.automaton.lr0_automaton import LR0Automaton
from src.core.parse_tree import ParseTree, ParseTreeNode
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class LR0Parser(ParserInterface):
    """LR(0) 语法分析器"""
    
    # 动作类型
    SHIFT = 's'    # 移进
    REDUCE = 'r'   # 归约
    ACCEPT = 'acc' # 接受
    GOTO = 'g'     # 转移
    
    def __init__(self, grammar: Grammar):
        """
        初始化 LR(0) 分析器
        :param grammar: 原始文法
        """
        super().__init__(grammar)
        self.augmented_grammar = None  # 增广文法
        self.automaton = None  # LR(0) 自动机
        self.action_table: Dict[Tuple[int, str], List[Tuple[str, int]]] = {}  # ACTION 表（支持多个动作）
        self.goto_table: Dict[Tuple[int, str], int] = {}  # GOTO 表
        self.has_conflicts = False  # 是否有冲突
        self.conflicts: List[str] = []  # 冲突列表
    
    def get_name(self) -> str:
        """获取分析器名称"""
        return "LR(0)"
    
    def build(self) -> bool:
        """
        构建 LR(0) 分析表
        :return: 是否构建成功（即使有冲突也返回 True，允许显示冲突信息）
        """
        # 步骤1：构造增广文法
        self.augmented_grammar = self._augment_grammar()
        
        # 步骤2：构造 LR(0) 自动机
        self.automaton = LR0Automaton(self.augmented_grammar)
        self.automaton.build()
        
        # 步骤3：构造分析表
        self._build_parsing_table()
        
        # 即使有冲突也返回 True，这样可以显示分析表和冲突信息
        return True
    
    def _augment_grammar(self) -> Grammar:
        """
        构造增广文法
        如果文法已经是增广文法（开始符号只有一个产生式，且右部只有一个非终结符和一个$），则直接返回
        否则增加新的开始符号 S' 和产生式 S' → S
        :return: 增广后的文法
        """
        original_start = self.grammar.start_symbol
        
        # 检查是否已经是增广文法
        # 增广文法的特征：开始符号只有一个产生式，且形如 S' -> S $ 或 S' -> S
        start_productions = [p for p in self.grammar.productions if p.left == original_start]
        
        if len(start_productions) == 1:
            prod = start_productions[0]
            # 检查是否形如 S' -> S $ 或 S' -> S
            if len(prod.right) >= 1:
                # 第一个符号是非终结符
                first_symbol = prod.right[0]
                if first_symbol in self.grammar.non_terminals:
                    # 如果只有一个符号，或者两个符号且第二个是 $
                    if len(prod.right) == 1 or (len(prod.right) == 2 and prod.right[1] == '$'):
                        # 这已经是增广文法，直接返回
                        # 注意：需要确保 $ 在终结符集合中
                        aug_grammar = Grammar()
                        aug_grammar.start_symbol = self.grammar.start_symbol
                        aug_grammar.non_terminals = self.grammar.non_terminals.copy()
                        aug_grammar.terminals = self.grammar.terminals.copy()
                        if '$' not in aug_grammar.terminals:
                            aug_grammar.terminals.add('$')
                        aug_grammar.productions = self.grammar.productions
                        
                        # 重新编号所有产生式
                        for i, prod in enumerate(aug_grammar.productions):
                            prod.index = i
                        
                        return aug_grammar
        
        # 不是增广文法，需要进行增广
        # 确定新的开始符号
        # 如果原开始符号没有 prime，则添加 prime
        # 如果已有 prime，则去掉 prime 后添加 _0
        if "'" in original_start:
            # 原符号已有 prime（如 S'），使用基础符号（如 S）
            base_symbol = original_start.rstrip("'")
            new_start = base_symbol + "_0"
            # 确保不冲突
            counter = 0
            while new_start in self.grammar.non_terminals:
                counter += 1
                new_start = base_symbol + f"_{counter}"
        else:
            # 原符号没有 prime，添加 prime
            new_start = original_start + "'"
            while new_start in self.grammar.non_terminals:
                new_start += "'"
        
        # 创建增广产生式 S' → S
        aug_production = Production(new_start, [original_start], 0)
        
        # 创建新文法
        aug_grammar = Grammar()
        aug_grammar.start_symbol = new_start
        aug_grammar.non_terminals = self.grammar.non_terminals.copy()
        aug_grammar.non_terminals.add(new_start)
        aug_grammar.terminals = self.grammar.terminals.copy()
        
        # 产生式列表以增广产生式开头
        aug_grammar.productions = [aug_production] + self.grammar.productions
        
        # 重新编号所有产生式
        for i, prod in enumerate(aug_grammar.productions):
            prod.index = i
        
        return aug_grammar
    
    def _build_parsing_table(self):
        """构造 LR(0) 分析表（ACTION 和 GOTO）"""
        self.action_table.clear()
        self.goto_table.clear()
        self.conflicts.clear()
        self.has_conflicts = False
        
        # 获取所有终结符（包括结束符 $）
        terminals = sorted(list(self.augmented_grammar.terminals))
        if '$' not in terminals:
            terminals.append('$')
        
        # 遍历所有状态
        for state in self.automaton.states:
            state_id = state.state_id
            
            # 处理状态中的每一项
            for item in state:
                if item.is_reducible():
                    # 归约项
                    self._add_reduce_action(state_id, item, terminals)
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
    
    def _add_shift_action(self, state_id: int, terminal: str):
        """
        添加移进动作
        :param state_id: 状态编号
        :param terminal: 终结符
        """
        target_state = self.automaton.get_transition(state_id, terminal)
        if target_state is not None:
            key = (state_id, terminal)
            action = (self.SHIFT, target_state)
            
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
                        conflict_type = "移进-移进冲突"
                    elif existing_type == self.REDUCE:
                        conflict_type = "移进-归约冲突"
                    else:
                        conflict_type = "冲突"
                    
                    conflict_msg = f"{conflict_type}: 状态 {state_id} 在符号 '{terminal}' 上，{self._format_action(existing_first)} 与 {self._format_action(action)}"
                    self.conflicts.append(conflict_msg)
                    
                    # 将新动作添加到列表
                    self.action_table[key].append(action)
            else:
                # 第一个动作，创建列表
                self.action_table[key] = [action]
    
    def _add_reduce_action(self, state_id: int, item: LRItem, terminals: List[str]):
        """
        添加归约动作（LR(0) 对所有终结符都归约）
        :param state_id: 状态编号
        :param item: 归约项
        :param terminals: 所有终结符
        """
        # 如果是增广产生式 S' → S·，不添加归约（由接受状态处理）
        if item.production.index == 0:
            return
        
        # 对所有终结符添加归约动作
        for terminal in terminals:
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
    
    def _add_goto_action(self, state_id: int, non_terminal: str):
        """
        添加 GOTO 动作
        :param state_id: 状态编号
        :param non_terminal: 非终结符
        """
        target_state = self.automaton.get_transition(state_id, non_terminal)
        if target_state is not None:
            key = (state_id, non_terminal)
            self.goto_table[key] = target_state
    
    def _check_accept_state(self, state_id: int, state: ItemSet):
        """
        检查是否是接受状态
        接受状态：包含 S' → S· 且点在最右边
        :param state_id: 状态编号
        :param state: 项集
        """
        for item in state:
            if (item.production.index == 0 and 
                item.is_reducible()):
                # 这是接受状态
                key = (state_id, '$')
                self.action_table[key] = [(self.ACCEPT, -1)]
                break
    
    def parse(self, sentence: List[str]) -> Tuple[bool, List]:
        """
        解析句子
        :param sentence: 输入句子（符号列表）
        :return: (是否成功, 分析步骤列表)
        """
        # 在输入末尾添加结束符
        input_symbols = sentence + ['$']
        
        # 初始化栈和指针（状态从1开始）
        state_stack = [1]  # 状态栈，初始状态为 1
        symbol_stack = ['$']  # 符号栈，初始时压入结束符
        tree_node_stack = []  # 语法树节点栈（用于构建语法树）
        input_index = 0    # 输入指针
        
        # 记录分析步骤
        steps = []
        step_num = 0  # 从0开始，显示初始状态
        
        # 添加初始状态步骤
        remaining = ' '.join(input_symbols)
        steps.append({
            'step': step_num,
            'state_stack': state_stack.copy(),
            'symbol_stack': symbol_stack.copy(),
            'input': remaining,
            'action': '初始状态',
            'tree_stack': []
        })
        step_num = 1
        
        while True:
            current_state = state_stack[-1]
            current_input = input_symbols[input_index] if input_index < len(input_symbols) else '$'
            
            # 查找动作
            action_key = (current_state, current_input)
            if action_key not in self.action_table:
                # 出错
                remaining = ' '.join(input_symbols[input_index:])
                steps.append({
                    'step': step_num,
                    'state_stack': state_stack.copy(),
                    'symbol_stack': symbol_stack.copy(),
                    'input': remaining,
                    'action': f'ERROR: 无效动作',
                    'tree_stack': None
                })
                return False, steps
            
            # 获取动作列表（可能有多个冲突的动作）
            actions = self.action_table[action_key]
            
            # 如果有冲突，使用第一个动作（也可以提示用户选择）
            if len(actions) > 1:
                action_type, action_value = actions[0]
                # 可以在这里添加警告
            else:
                action_type, action_value = actions[0]
            
            # 执行动作
            if action_type == self.SHIFT:
                # 移进
                state_stack.append(action_value)
                symbol_stack.append(current_input)
                
                # 为移进的终结符创建叶子节点
                terminal_node = ParseTreeNode(current_input, is_terminal=True)
                tree_node_stack.append(terminal_node)
                
                remaining = ' '.join(input_symbols[input_index + 1:])
                steps.append({
                    'step': step_num,
                    'state_stack': state_stack.copy(),
                    'symbol_stack': symbol_stack.copy(),
                    'input': remaining,
                    'action': f'移进到状态 {action_value}',
                    'tree_stack': tree_node_stack.copy()
                })
                
                input_index += 1
                step_num += 1
                
            elif action_type == self.REDUCE:
                # 归约
                production = self.augmented_grammar.productions[action_value]
                
                # 弹出产生式右部长度的符号和状态
                pop_count = len(production.right) if not production.is_epsilon() else 0
                
                # 创建新的非终结符节点
                new_node = ParseTreeNode(production.left, is_terminal=False)
                new_node.production = production
                
                # 从树节点栈中弹出子节点并添加到新节点
                children_nodes = []
                for _ in range(pop_count):
                    if symbol_stack:
                        symbol_stack.pop()
                    if len(state_stack) > 1:
                        state_stack.pop()
                    if tree_node_stack:
                        children_nodes.append(tree_node_stack.pop())
                
                # 反转子节点顺序（因为是从栈中弹出的）
                children_nodes.reverse()
                for child in children_nodes:
                    new_node.add_child(child)
                
                # 如果是 epsilon 产生式，添加一个 epsilon 叶子节点
                if production.is_epsilon():
                    epsilon_node = ParseTreeNode('ε', is_terminal=True)
                    new_node.add_child(epsilon_node)
                
                # 压入产生式左部
                symbol_stack.append(production.left)
                tree_node_stack.append(new_node)
                
                # 查找 GOTO
                goto_key = (state_stack[-1], production.left)
                if goto_key in self.goto_table:
                    next_state = self.goto_table[goto_key]
                    state_stack.append(next_state)
                else:
                    remaining = ' '.join(input_symbols[input_index:])
                    steps.append({
                        'step': step_num,
                        'state_stack': state_stack.copy(),
                        'symbol_stack': symbol_stack.copy(),
                        'input': remaining,
                        'action': f'ERROR: 无效 GOTO',
                        'tree_stack': tree_node_stack.copy()
                    })
                    return False, steps
                
                remaining = ' '.join(input_symbols[input_index:])
                steps.append({
                    'step': step_num,
                    'state_stack': state_stack.copy(),
                    'symbol_stack': symbol_stack.copy(),
                    'input': remaining,
                    'action': f'用 {production} 归约',
                    'tree_stack': tree_node_stack.copy()
                })
                
                step_num += 1
                
            elif action_type == self.ACCEPT:
                # 接受
                steps.append({
                    'step': step_num,
                    'state_stack': state_stack.copy(),
                    'symbol_stack': symbol_stack.copy(),
                    'input': '',
                    'action': '接受',
                    'tree_stack': tree_node_stack.copy()
                })
                
                # 创建完整的语法树
                if tree_node_stack:
                    # 最后的节点应该是根节点
                    root = tree_node_stack[-1]
                    parse_tree = ParseTree(root.symbol)
                    parse_tree.root = root
                    steps[-1]['parse_tree'] = parse_tree
                
                return True, steps
            
            else:
                # 未知动作
                remaining = ' '.join(input_symbols[input_index:])
                steps.append({
                    'step': step_num,
                    'state_stack': state_stack.copy(),
                    'symbol_stack': symbol_stack.copy(),
                    'input': remaining,
                    'action': f'ERROR: 未知动作',
                    'tree_stack': tree_node_stack.copy()
                })
                return False, steps
    
    def _format_action(self, action: Tuple[str, int]) -> str:
        """
        格式化动作为可读字符串
        :param action: (动作类型, 值)
        :return: 格式化的字符串
        """
        action_type, value = action
        if action_type == self.SHIFT:
            return f"移进到状态 {value}"
        elif action_type == self.REDUCE:
            prod = self.augmented_grammar.productions[value]
            return f"用产生式 ({value}) {prod} 归约"
        elif action_type == self.ACCEPT:
            return "接受"
        else:
            return str(action)
    
    def print_table(self):
        """打印 LR(0) 分析表"""
        console = Console()
        
        # 收集所有终结符和非终结符
        # 注意：如果 $ 已经在 terminals 中，就不重复添加
        terminals = sorted(self.augmented_grammar.terminals)
        if '$' not in terminals:
            terminals.append('$')
        non_terminals = sorted([nt for nt in self.augmented_grammar.non_terminals 
                               if nt != self.augmented_grammar.start_symbol])
        
        # 创建表格标题
        title = "LR(0) 分析表"
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
            console.print("  - [yellow]该文法不是 LR(0) 文法，建议尝试 SLR 或更强的分析算法[/yellow]")
    
    def print_dfa(self):
        """打印 DFA（项集规范族）"""
        console = Console()
        
        console.print("\n[bold cyan]LR(0) 项集规范族（DFA）[/bold cyan]\n")
        
        for state in self.automaton.states:
            # 创建项集面板
            items_str = '\n'.join(str(item) for item in sorted(state.items,
                                  key=lambda x: (x.production.index, x.dot_position)))
            
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
