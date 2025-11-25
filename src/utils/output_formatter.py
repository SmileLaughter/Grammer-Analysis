"""
输出格式化模块
使用rich库美化输出
"""

from typing import Dict, Set, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from src.core.grammar import Grammar, Production
from src.core.first_follow import FirstFollowCalculator


class OutputFormatter:
    """输出格式化器"""
    
    def __init__(self):
        """初始化格式化器"""
        self.console = Console()
    
    def print_grammar(self, grammar: Grammar):
        """
        打印文法信息
        :param grammar: 文法对象
        """
        # 创建文法信息面板
        info_text = Text()
        info_text.append("开始符号: ", style="bold yellow")
        info_text.append(f"{grammar.start_symbol}\n", style="cyan")
        info_text.append("非终结符: ", style="bold yellow")
        info_text.append(f"{sorted(grammar.non_terminals)}\n", style="cyan")
        info_text.append("终结符: ", style="bold yellow")
        info_text.append(f"{sorted(grammar.terminals)}", style="cyan")
        
        panel = Panel(info_text, title="[bold magenta]文法信息[/bold magenta]", 
                     border_style="magenta")
        self.console.print(panel)
        
        # 打印产生式
        self.console.print("\n[bold magenta]产生式列表:[/bold magenta]")
        for i, prod in enumerate(grammar.productions):
            right_str = ' '.join(prod.right) if prod.right else 'ε'
            self.console.print(f"  [yellow]({i})[/yellow] [cyan]{prod.left}[/cyan] → {right_str}")
    
    def print_nullable_set(self, nullable: Set[str]):
        """
        打印NULLABLE集
        :param nullable: NULLABLE集合
        """
        table = Table(title="NULLABLE 集", show_header=True, header_style="bold magenta")
        table.add_column("非终结符", style="cyan", justify="center")
        table.add_column("是否NULLABLE", justify="center")
        
        # 获取所有非终结符并排序
        all_non_terminals = sorted(nullable)
        
        for nt in all_non_terminals:
            table.add_row(nt, "[green]✓[/green]")
        
        self.console.print("\n")
        self.console.print(table)
    
    def print_first_sets(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        打印每个非终结符的FIRST集
        :param grammar: 文法对象
        :param calculator: FIRST/FOLLOW计算器
        """
        table = Table(title="非终结符的 FIRST 集", show_header=True, header_style="bold magenta")
        table.add_column("非终结符", style="cyan", justify="center")
        table.add_column("FIRST 集", justify="left")
        
        # 按字母顺序排序非终结符
        for nt in sorted(grammar.non_terminals):
            first_set = calculator.get_first_set(nt)
            first_str = ', '.join(sorted(first_set)) if first_set else '∅'
            table.add_row(nt, f"{{ {first_str} }}")
        
        self.console.print("\n")
        self.console.print(table)
    
    def print_follow_sets(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        打印每个非终结符的FOLLOW集
        :param grammar: 文法对象
        :param calculator: FIRST/FOLLOW计算器
        """
        table = Table(title="非终结符的 FOLLOW 集", show_header=True, header_style="bold magenta")
        table.add_column("非终结符", style="cyan", justify="center")
        table.add_column("FOLLOW 集", justify="left")
        
        # 按字母顺序排序非终结符
        for nt in sorted(grammar.non_terminals):
            # 使用 get_follow_set_for_display 获取FOLLOW集
            follow_set = calculator.get_follow_set_for_display(nt)
            follow_str = ', '.join(sorted(follow_set)) if follow_set else '∅'
            table.add_row(nt, f"{{ {follow_str} }}")
        
        self.console.print("\n")
        self.console.print(table)
    
    def print_production_first_sets(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        打印每个产生式的FIRST集（实际是SELECT集）
        :param grammar: 文法对象
        :param calculator: FIRST/FOLLOW计算器
        """
        table = Table(title="产生式的 FIRST 集", show_header=True, header_style="bold magenta")
        table.add_column("编号", style="yellow", justify="center")
        table.add_column("产生式", style="cyan", justify="left")
        table.add_column("FIRST 集", justify="left")
        
        for prod in grammar.productions:
            # 使用SELECT集而不是原始的FIRST集
            select_set = calculator.get_select_set(prod)
            select_str = ', '.join(sorted(select_set)) if select_set else '∅'
            
            # 格式化产生式
            right_str = ' '.join(prod.right) if prod.right else 'ε'
            prod_str = f"{prod.left} → {right_str}"
            
            table.add_row(str(prod.index), prod_str, f"{{ {select_str} }}")
        
        self.console.print("\n")
        self.console.print(table)
    
    def print_select_sets(self, grammar: Grammar, calculator: FirstFollowCalculator):
        """
        打印每个产生式的SELECT集（用于LL(1)分析）
        :param grammar: 文法对象
        :param calculator: FIRST/FOLLOW计算器
        """
        table = Table(title="产生式的 SELECT 集（用于 LL(1) 分析）", show_header=True, header_style="bold magenta")
        table.add_column("编号", style="yellow", justify="center")
        table.add_column("产生式", style="cyan", justify="left")
        table.add_column("SELECT 集", justify="left")
        
        for prod in grammar.productions:
            select_set = calculator.get_select_set(prod)
            select_str = ', '.join(sorted(select_set)) if select_set else '∅'
            
            # 格式化产生式
            right_str = ' '.join(prod.right) if prod.right else 'ε'
            prod_str = f"{prod.left} → {right_str}"
            
            table.add_row(str(prod.index), prod_str, f"{{ {select_str} }}")
        
        self.console.print("\n")
        self.console.print(table)

    
    def print_parsing_steps(self, steps: List[Dict], success: bool):
        """
        打印语法分析步骤
        :param steps: 分析步骤列表
        :param success: 是否分析成功
        """
        # 创建步骤表格，启用行分隔符
        table = Table(
            title="语法分析过程", 
            show_header=True, 
            header_style="bold magenta",
            show_lines=True  # 启用行之间的分隔线
        )
        # 不设置固定宽度，让表格自适应内容宽度
        table.add_column("步骤", style="yellow", justify="center")
        table.add_column("栈", style="cyan", justify="left")
        table.add_column("未处理的字符", style="green", justify="left")
        table.add_column("动作", justify="left")
        
        for step in steps:
            # 根据动作类型选择颜色
            action = step['action']
            if '错误' in action or 'ERROR' in action:
                action_style = "[red]" + action + "[/red]"
            elif '接受' in action:
                action_style = "[bold green]" + action + "[/bold green]"
            else:
                action_style = action
            
            # 处理栈的显示（兼容 LL(1) 和 LR 格式）
            if 'stack' in step:
                # LL(1) 格式
                stack_str = step['stack']
            elif 'symbol_stack' in step and 'state_stack' in step:
                # LR 格式：上下结构显示状态栈和记号栈
                symbols = step['symbol_stack']
                states = step['state_stack']
                
                # 状态栈：显示所有状态
                state_line = "状态栈: " + " ".join(str(s) for s in states)
                
                # 记号栈：显示所有符号
                symbol_line = "记号栈: " + " ".join(symbols) if symbols else "记号栈: "
                
                # 组合成上下两行
                stack_str = state_line + "\n" + symbol_line
            else:
                stack_str = str(step.get('stack', ''))
            
            table.add_row(
                str(step['step']),
                stack_str,
                step['input'],
                action_style
            )
        
        self.console.print("\n")
        self.console.print(table)
        
        # 打印分析结果
        if success:
            self.console.print("\n[bold green]✓ 分析成功！句子符合文法。[/bold green]")
        else:
            self.console.print("\n[bold red]✗ 分析失败！句子不符合文法。[/bold red]")
    
    def print_error(self, message: str):
        """
        打印错误消息
        :param message: 错误消息
        """
        self.console.print(f"[bold red]错误: {message}[/bold red]")
    
    def print_success(self, message: str):
        """
        打印成功消息
        :param message: 成功消息
        """
        self.console.print(f"[bold green]✓ {message}[/bold green]")
    
    def print_info(self, message: str):
        """
        打印信息消息
        :param message: 信息消息
        """
        self.console.print(f"[bold cyan]ℹ {message}[/bold cyan]")
    
    def print_separator(self):
        """打印分隔线"""
        self.console.print("\n" + "=" * 80 + "\n")
