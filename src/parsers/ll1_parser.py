"""
LL(1)语法分析器模块
包含冲突检测、自动转换和分析功能
"""

from typing import List, Tuple, Dict, Set, Any, Optional
from src.core.grammar import Grammar, Production
from src.core.first_follow import FirstFollowCalculator
from src.core.parser_interface import ParserInterface
from src.utils.grammar_transformer import GrammarTransformer
from collections import defaultdict
from rich.table import Table
from rich.console import Console


class LL1Parser(ParserInterface):
    """LL(1)语法分析器"""
    
    def __init__(self, grammar: Grammar):
        """
        初始化LL(1)分析器
        :param grammar: 文法对象
        """
        super().__init__(grammar)
        # LL(1) 分析需要 $ 符号来处理输入结束的情况
        # 例如：A -> ε 的 SELECT 集 = FOLLOW(A)，其中可能包含 $
        self.calculator = FirstFollowCalculator(grammar, include_dollar=True)
        
        # LL(1)分析表：M[非终结符][终结符] = 产生式列表（支持冲突显示）
        self.parsing_table: Dict[str, Dict[str, List[Production]]] = defaultdict(lambda: defaultdict(list))
        
        # 是否构建成功
        self.is_built = False
        
        # 冲突记录
        self.conflicts: List[str] = []
    
    def build(self) -> bool:
        """
        构建LL(1)分析表
        :return: 是否构建成功（无冲突）
        """
        # 首先计算FIRST和FOLLOW集
        self.calculator.calculate_all()
        
        # 清空分析表和冲突记录
        self.parsing_table.clear()
        self.conflicts.clear()
        
        # 构建分析表 - 使用SELECT集
        for prod in self.grammar.productions:
            # 获取产生式的SELECT集（即产生式的FIRST集，已包含FOLLOW集的处理）
            select_set = self.calculator.get_select_set(prod)
            
            # 对于SELECT集中的每个终结符，将M[A][terminal]设置为该产生式
            for terminal in select_set:
                self._add_to_table(prod.left, terminal, prod)
        
        # 检查是否有冲突
        self.is_built = len(self.conflicts) == 0
        return self.is_built
    
    def _production_is_nullable(self, prod: Production) -> bool:
        """
        判断产生式右部是否可以推导出epsilon
        :param prod: 产生式
        :return: 是否可以推导出epsilon
        """
        # 如果是epsilon产生式，直接返回True
        if prod.is_epsilon():
            return True
        
        # 检查右部的所有符号是否都是nullable
        nullable_set = self.calculator.get_nullable_set()
        return all(symbol in nullable_set for symbol in prod.right)
    
    def _add_to_table(self, non_terminal: str, terminal: str, production: Production):
        """
        向分析表中添加条目
        :param non_terminal: 非终结符
        :param terminal: 终结符
        :param production: 产生式
        """
        # 获取该单元格的产生式列表
        prod_list = self.parsing_table[non_terminal][terminal]
        
        # 检查是否已存在该产生式
        if production not in prod_list:
            prod_list.append(production)
            
            # 如果有多个产生式，记录冲突
            if len(prod_list) > 1:
                # 构造冲突信息，包含产生式编号
                prod_strs = [f"({p.index}) {p}" for p in prod_list]
                conflict_msg = (
                    f"冲突: M[{non_terminal}][{terminal}] = "
                    f"{' 与 '.join(prod_strs)}"
                )
                # 只在第一次出现冲突时添加（避免重复）
                if conflict_msg not in self.conflicts:
                    self.conflicts.append(conflict_msg)
    
    def parse(self, sentence: List[str]) -> Tuple[bool, Any]:
        """
        使用LL(1)分析表解析句子
        :param sentence: 待解析的句子
        :return: (是否解析成功, 分析步骤列表)
        """
        if not self.is_built:
            return False, "分析表未构建或存在冲突"
        
        # 初始化栈和输入
        stack = ['$', self.grammar.start_symbol]  # 栈底是$，然后是开始符号
        input_symbols = sentence + ['$']  # 输入串末尾加$
        input_index = 0  # 当前输入指针
        
        # 分析步骤记录
        steps = []
        step_num = 0
        
        # 开始分析
        while True:
            step_num += 1
            
            # 获取栈顶符号和当前输入符号
            top = stack[-1]
            current_input = input_symbols[input_index]
            
            # 记录当前步骤
            stack_str = ' '.join(reversed(stack))
            remaining_input = ' '.join(input_symbols[input_index:])
            
            # 如果栈顶是$
            if top == '$':
                if current_input == '$':
                    # 分析成功
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': '接受'
                    })
                    return True, steps
                else:
                    # 输入还未结束但栈已空，分析失败
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': '错误：输入未结束'
                    })
                    return False, steps
            
            # 如果栈顶是终结符
            if top in self.grammar.terminals:
                if top == current_input:
                    # 匹配成功，弹出栈顶，移动输入指针
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': f'匹配 {top}'
                    })
                    stack.pop()
                    input_index += 1
                else:
                    # 匹配失败
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': f'错误：期望 {top}，得到 {current_input}'
                    })
                    return False, steps
            
            # 如果栈顶是非终结符
            elif top in self.grammar.non_terminals:
                # 查找分析表
                if current_input in self.parsing_table[top]:
                    prod_list = self.parsing_table[top][current_input]
                    
                    # 如果有冲突（多个产生式），使用第一个
                    if not prod_list:
                        steps.append({
                            'step': step_num,
                            'stack': stack_str,
                            'input': remaining_input,
                            'action': f'错误：M[{top}][{current_input}] 为空'
                        })
                        return False, steps
                    
                    production = prod_list[0]  # 使用第一个产生式
                    
                    # 记录使用的产生式（显示编号）
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': f'使用产生式 ({production.index}) {production}'
                    })
                    
                    # 弹出栈顶非终结符
                    stack.pop()
                    
                    # 将产生式右部逆序压栈（如果不是epsilon产生式）
                    if not production.is_epsilon():
                        for symbol in reversed(production.right):
                            stack.append(symbol)
                else:
                    # 分析表中没有对应条目
                    steps.append({
                        'step': step_num,
                        'stack': stack_str,
                        'input': remaining_input,
                        'action': f'错误：M[{top}][{current_input}] 为空'
                    })
                    return False, steps
            else:
                # 未知符号
                steps.append({
                    'step': step_num,
                    'stack': stack_str,
                    'input': remaining_input,
                    'action': f'错误：未知符号 {top}'
                })
                return False, steps
    
    def print_table(self):
        """使用rich库打印LL(1)分析表"""
        console = Console()
        
        # 创建表格
        table = Table(title="LL(1) 分析表", show_header=True, header_style="bold magenta")
        
        # 获取所有终结符（不包括$）
        terminals = sorted(self.grammar.terminals)
        
        # 检查是否有任何非终结符在$列有条目
        has_dollar_column = False
        for non_terminal in self.grammar.non_terminals:
            if '$' in self.parsing_table[non_terminal]:
                prod_list = self.parsing_table[non_terminal]['$']
                if prod_list:
                    has_dollar_column = True
                    break
        
        # 只有在确实使用$列时才添加
        if has_dollar_column:
            terminals.append('$')
        
        # 添加列：第一列是非终结符，其余列是终结符
        table.add_column("非终结符", style="cyan", justify="center")
        for terminal in terminals:
            table.add_column(terminal, justify="center")
        
        # 添加行
        for non_terminal in sorted(self.grammar.non_terminals):
            row = [non_terminal]
            for terminal in terminals:
                if terminal in self.parsing_table[non_terminal]:
                    prod_list = self.parsing_table[non_terminal][terminal]
                    if prod_list:
                        # 只显示产生式编号，多个产生式用逗号分隔
                        indices = [str(prod.index) for prod in prod_list]
                        cell_text = ', '.join(indices)
                        row.append(cell_text)
                    else:
                        row.append("")
                else:
                    row.append("")
            table.add_row(*row)
        
        # 打印表格
        console.print(table)
        
        # 如果有冲突，打印冲突信息
        if self.conflicts:
            console.print(f"\n[bold red]检测到 {len(self.conflicts)} 个冲突：[/bold red]")
            for i, conflict in enumerate(self.conflicts, 1):
                console.print(f"  [red]{i}. {conflict}[/red]")
    
    def get_name(self) -> str:
        """获取分析器名称"""
        return "LL(1)"
    
    def build_with_transform(self, console: Console) -> Tuple[bool, Optional[Grammar]]:
        """
        构建分析表，如果失败则尝试自动转换文法
        :param console: Rich Console 对象用于输出
        :return: (是否成功, 转换后的文法或None)
        """
        # 先尝试直接构建
        if self.build():
            return True, None
        
        # 构建失败，显示冲突信息
        console.print("\n[bold red]✗ 原始文法不满足 LL(1) 条件[/bold red]")
        
        # 显示有冲突的分析表
        console.print("\n[bold magenta]原始文法的 LL(1) 分析表（含冲突）：[/bold magenta]")
        self.print_table()
        
        # 显示冲突详情
        if self.conflicts:
            console.print(f"\n[bold red]检测到 {len(self.conflicts)} 个冲突：[/bold red]")
            for i, conflict in enumerate(self.conflicts, 1):
                console.print(f"  [red]{i}. {conflict}[/red]")
        
        return False, None
    
    def try_auto_transform(self, console: Console) -> Tuple[bool, Optional[Grammar], List[str]]:
        """
        尝试自动转换文法以解决冲突
        :param console: Rich Console 对象用于输出
        :return: (是否成功, 转换后的文法或None, 转换步骤列表)
        """
        console.print("\n[bold yellow]正在尝试自动转换文法...[/bold yellow]\n")
        
        # 显示转换规则
        console.print("[cyan]应用转换规则：[/cyan]")
        console.print("  (1) 基于产生式的 FIRST 集相交 → 提取左公因子")
        console.print("  (2) 存在空串产生式：")
        console.print("      ① 如果 α 或 β 可推导出空串 → 展开产生式，消除左递归或提取左公因子")
        console.print("      ② 如果 α 和 β 都可推导出空串 → 删除其中一个 ε\n")
        
        # 执行转换
        transformer = GrammarTransformer(self.grammar)
        transformed_grammar, success, transformations = transformer.transform_to_ll1()
        
        # 显示转换步骤
        if transformations:
            console.print("[bold cyan]执行的转换步骤：[/bold cyan]")
            for i, trans in enumerate(transformations, 1):
                console.print(f"  [cyan]{i}. {trans}[/cyan]")
        else:
            console.print("[yellow]未执行任何转换（可能无法自动解决冲突）[/yellow]")
        
        return success, transformed_grammar, transformations
    
    def show_transform_result(self, success: bool, transformed_grammar: Grammar, 
                            transformations: List[str], console: Console):
        """
        显示转换结果
        :param success: 转换是否成功
        :param transformed_grammar: 转换后的文法
        :param transformations: 转换步骤列表
        :param console: Rich Console 对象
        """
        from src.utils.output_formatter import OutputFormatter
        formatter = OutputFormatter()
        
        if success:
            # 转换成功
            console.print("\n[bold green]✓ 成功将文法转换为 LL(1) 文法！[/bold green]\n")
            
            # 显示转换后的文法
            console.print("[bold magenta]转换后的文法：[/bold magenta]")
            formatter.print_grammar(transformed_grammar)
            
            # 重新计算集合
            new_calculator = FirstFollowCalculator(transformed_grammar, include_dollar=True)
            new_calculator.calculate_all()
            
            # 显示新的集合
            formatter.print_nullable_set(new_calculator.get_nullable_set())
            formatter.print_first_sets(transformed_grammar, new_calculator)
            formatter.print_follow_sets(transformed_grammar, new_calculator)
            formatter.print_production_first_sets(transformed_grammar, new_calculator)
            
            # 构建新的分析表
            console.print("\n[bold magenta]转换后的 LL(1) 分析表（无冲突）：[/bold magenta]")
            new_parser = LL1Parser(transformed_grammar)
            if new_parser.build():
                new_parser.print_table()
            else:
                console.print("[red]错误：转换后仍有冲突（不应该发生）[/red]")
        else:
            # 转换失败
            console.print("\n[bold red]✗ 无法将文法自动转换为 LL(1) 文法[/bold red]\n")
            
            # 显示转换尝试后的文法（可能有部分改进）
            if transformations:
                console.print("[bold magenta]转换尝试后的文法：[/bold magenta]")
                formatter.print_grammar(transformed_grammar)
            
            # 构建分析表看看剩余的冲突
            new_calculator = FirstFollowCalculator(transformed_grammar, include_dollar=True)
            new_calculator.calculate_all()
            
            new_parser = LL1Parser(transformed_grammar)
            new_parser.build()
            
            console.print("\n[bold magenta]转换后的 LL(1) 分析表（仍有冲突）：[/bold magenta]")
            new_parser.print_table()
            
            # 显示剩余冲突
            if new_parser.conflicts:
                console.print(f"\n[bold red]剩余 {len(new_parser.conflicts)} 个冲突：[/bold red]")
                for i, conflict in enumerate(new_parser.conflicts, 1):
                    console.print(f"  [red]{i}. {conflict}[/red]")
            
            # 详细分析冲突原因
            self.analyze_conflicts(transformed_grammar, new_calculator, console)
    
    def analyze_conflicts(self, grammar: Grammar, calculator: FirstFollowCalculator, 
                         console: Console):
        """
        详细分析文法冲突原因
        :param grammar: 文法对象
        :param calculator: FIRST/FOLLOW 计算器
        :param console: Rich Console 对象
        """
        console.print("\n[bold red]冲突原因详细分析：[/bold red]\n")
        
        found_conflict = False
        
        for nt in sorted(grammar.non_terminals):
            prods = grammar.get_productions_for(nt)
            if len(prods) < 2:
                continue
            
            # 检查每对产生式的冲突
            for i in range(len(prods)):
                for j in range(i + 1, len(prods)):
                    first1 = calculator.get_production_first_set(prods[i])
                    first2 = calculator.get_production_first_set(prods[j])
                    
                    # 检查 FIRST 集冲突
                    intersection = first1 & first2
                    if intersection:
                        found_conflict = True
                        console.print(f"[bold red]非终结符 '{nt}' 的 FIRST 集冲突：[/bold red]")
                        console.print(f"  产生式1: [cyan]{prods[i]}[/cyan]")
                        console.print(f"    FIRST = {{{', '.join(sorted(first1))}}}")
                        console.print(f"  产生式2: [cyan]{prods[j]}[/cyan]")
                        console.print(f"    FIRST = {{{', '.join(sorted(first2))}}}")
                        console.print(f"  [red]✗ 交集 = {{{', '.join(sorted(intersection))}}}[/red]")
                        console.print(f"  [yellow]原因: FIRST 集有公共元素 {intersection}[/yellow]")
                        
                        # 分析是否可以提取左公因子
                        common_prefix = self._find_common_prefix(prods[i].right, prods[j].right)
                        if common_prefix:
                            console.print(f"  [green]建议: 可以提取左公因子 '{' '.join(common_prefix)}'[/green]")
                        else:
                            console.print(f"  [yellow]说明: 无公共前缀，无法提取左公因子[/yellow]")
                        console.print()
                    
                    # 检查 FIRST-FOLLOW 冲突
                    is_nullable1 = self._is_production_nullable(prods[i], calculator)
                    is_nullable2 = self._is_production_nullable(prods[j], calculator)
                    
                    if is_nullable1 or is_nullable2:
                        follow = calculator.get_follow_set(nt)
                        
                        if is_nullable1:
                            ff_intersection = first2 & follow
                            if ff_intersection:
                                found_conflict = True
                                console.print(f"[bold red]非终结符 '{nt}' 的 FIRST-FOLLOW 冲突：[/bold red]")
                                console.print(f"  产生式1: [cyan]{prods[i]}[/cyan] (可推导出 ε)")
                                console.print(f"  产生式2: [cyan]{prods[j]}[/cyan]")
                                console.print(f"    FIRST = {{{', '.join(sorted(first2))}}}")
                                console.print(f"  FOLLOW({nt}) = {{{', '.join(sorted(follow))}}}")
                                console.print(f"  [red]✗ 交集 = {{{', '.join(sorted(ff_intersection))}}}[/red]")
                                console.print(f"  [yellow]原因: ε 产生式导致 FIRST 与 FOLLOW 集冲突[/yellow]")
                                console.print(f"  [yellow]说明: 当遇到 {ff_intersection} 时，无法决定是使用 ε 产生式还是其他产生式[/yellow]")
                                console.print()
                        
                        if is_nullable2 and not is_nullable1:
                            ff_intersection = first1 & follow
                            if ff_intersection:
                                found_conflict = True
                                console.print(f"[bold red]非终结符 '{nt}' 的 FIRST-FOLLOW 冲突：[/bold red]")
                                console.print(f"  产生式1: [cyan]{prods[j]}[/cyan] (可推导出 ε)")
                                console.print(f"  产生式2: [cyan]{prods[i]}[/cyan]")
                                console.print(f"    FIRST = {{{', '.join(sorted(first1))}}}")
                                console.print(f"  FOLLOW({nt}) = {{{', '.join(sorted(follow))}}}")
                                console.print(f"  [red]✗ 交集 = {{{', '.join(sorted(ff_intersection))}}}[/red]")
                                console.print(f"  [yellow]原因: ε 产生式导致 FIRST 与 FOLLOW 集冲突[/yellow]")
                                console.print()
        
        if not found_conflict:
            console.print("[yellow]未检测到明显的冲突（可能是其他问题）[/yellow]\n")
        
        # 总结
        console.print("[bold yellow]结论：[/bold yellow]")
        console.print("  该文法无法通过简单的自动转换变为 LL(1) 文法。")
        console.print("  建议手动重新设计文法，或考虑使用更强大的分析算法（如 LR 分析）。\n")
    
    def _is_production_nullable(self, prod: Production, calculator: FirstFollowCalculator) -> bool:
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
