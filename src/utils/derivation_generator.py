"""
推导生成器
用于生成最左推导和最右推导，并可视化语法分析树
"""

from typing import List, Tuple, Optional
from src.core.grammar import Grammar, Production
from src.parsers.ll1_parser import LL1Parser
from rich.console import Console
from rich.table import Table


class DerivationStep:
    """推导步骤"""
    
    def __init__(self, sentential_form: List[str], production: Optional[Production], position: int):
        """
        初始化推导步骤
        :param sentential_form: 句型（推导过程中的符号串）
        :param production: 使用的产生式
        :param position: 替换位置（最左/最右非终结符的位置）
        """
        self.sentential_form = sentential_form
        self.production = production
        self.position = position


class DerivationGenerator:
    """推导生成器"""
    
    def __init__(self, grammar: Grammar, console: Console = None):
        """
        初始化生成器
        :param grammar: 文法
        :param console: Rich Console 对象
        """
        self.grammar = grammar
        self.console = console or Console()
        self.ll1_parser = None
    
    def generate_leftmost_derivation(self, sentence: List[str]) -> Tuple[bool, List[DerivationStep]]:
        """
        生成最左推导
        新方法：首先尝试使用通用回溯搜索，如果失败则尝试 LR(1) 分析器
        
        :param sentence: 目标句子
        :return: (是否成功, 推导步骤列表)
        """
        # 首先尝试使用通用推导生成器（支持任意CFG）
        from src.utils.universal_derivation import UniversalDerivationGenerator
        
        universal_gen = UniversalDerivationGenerator(self.grammar, max_depth=200)
        success, raw_steps = universal_gen.generate_leftmost_derivation(sentence)
        
        if success:
            # 转换为 DerivationStep 格式
            derivation_steps = []
            for i, (sentential_form, production) in enumerate(raw_steps):
                # 计算替换位置
                position = 0
                if production is not None and i > 0:
                    prev_form = raw_steps[i-1][0]
                    # 找到被替换的非终结符位置
                    for j, symbol in enumerate(prev_form):
                        if symbol == production.left:
                            position = j
                            break
                derivation_steps.append(DerivationStep(sentential_form, production, position))
            return True, derivation_steps
        
        # 如果通用方法失败，尝试使用 LR(1) 分析器
        from src.parsers.lr1_parser import LR1Parser
        
        lr1_parser = LR1Parser(self.grammar)
        if not lr1_parser.build():
            return False, []
        
        # 使用 LR(1) 分析获取归约序列
        success, parse_result = lr1_parser.parse(sentence)
        if not success:
            return False, []
        
        # 从 LR(1) 解析步骤中提取归约使用的产生式
        # LR(1) 的归约顺序是最右推导的逆序
        productions_used = []
        import re
        for step_info in parse_result:
            if 'action' not in step_info:
                continue
            
            action = step_info['action']
            
            # 匹配归约动作：格式 "用 A → α 归约"
            match = re.search(r'用\s+(.+?)\s+→\s+(.+?)\s+归约', action)
            if match:
                left_symbol = match.group(1).strip()
                right_symbols = match.group(2).strip()
                
                # 在文法中查找匹配的产生式
                for prod in self.grammar.productions:
                    if prod.left == left_symbol:
                        # 检查右部是否匹配
                        prod_right_str = ' '.join(prod.right) if not prod.is_epsilon() else 'ε'
                        if prod_right_str == right_symbols or (right_symbols == 'ε' and prod.is_epsilon()):
                            productions_used.append(prod)
                            break
        
        # 将归约序列反转得到最右推导
        rightmost_productions = list(reversed(productions_used))
        
        # 从最右推导转换为最左推导
        # 关键思想：最右推导和最左推导使用相同的产生式集合，只是应用顺序不同
        # 我们需要重新排序这些产生式，使其符合最左推导的顺序
        
        leftmost_steps = self._convert_rightmost_to_leftmost(rightmost_productions)
        
        return True, leftmost_steps
    
    def _convert_rightmost_to_leftmost(self, rightmost_productions: List) -> List[DerivationStep]:
        """
        将最右推导的产生式序列转换为最左推导序列
        
        :param rightmost_productions: 最右推导使用的产生式列表
        :return: 最左推导的步骤列表
        """
        # 初始步骤
        derivation_steps = []
        current_form = [self.grammar.start_symbol]
        derivation_steps.append(DerivationStep(current_form.copy(), None, 0))
        
        # 将产生式按照它们的左部符号分组
        prod_dict = {}
        for prod in rightmost_productions:
            if prod.left not in prod_dict:
                prod_dict[prod.left] = []
            prod_dict[prod.left].append(prod)
        
        # 按最左推导的方式应用产生式
        # 最左推导：总是展开最左边的非终结符
        max_iterations = len(rightmost_productions) * 2  # 防止无限循环
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 找到最左边的非终结符
            leftmost_nt_pos = -1
            leftmost_nt = None
            for i, symbol in enumerate(current_form):
                if symbol in self.grammar.non_terminals:
                    leftmost_nt_pos = i
                    leftmost_nt = symbol
                    break
            
            if leftmost_nt is None:
                # 没有非终结符了，推导完成
                break
            
            # 查找这个非终结符对应的产生式
            if leftmost_nt not in prod_dict or len(prod_dict[leftmost_nt]) == 0:
                # 没有可用的产生式了，停止
                break
            
            # 使用第一个可用的产生式
            production = prod_dict[leftmost_nt].pop(0)
            
            # 替换非终结符
            new_form = current_form[:leftmost_nt_pos]
            if not production.is_epsilon():
                new_form.extend(production.right)
            new_form.extend(current_form[leftmost_nt_pos + 1:])
            
            current_form = new_form
            derivation_steps.append(DerivationStep(current_form.copy(), production, leftmost_nt_pos))
        
        return derivation_steps
    
    def generate_rightmost_derivation(self, sentence: List[str]) -> Tuple[bool, List[DerivationStep]]:
        """
        生成最右推导
        首先尝试使用通用回溯搜索，如果失败则从最左推导转换
        
        :param sentence: 目标句子
        :return: (是否成功, 推导步骤列表)
        """
        # 首先尝试使用通用推导生成器（支持任意CFG）
        from src.utils.universal_derivation import UniversalDerivationGenerator
        
        universal_gen = UniversalDerivationGenerator(self.grammar, max_depth=200)
        success, raw_steps = universal_gen.generate_rightmost_derivation(sentence)
        
        if success:
            # 转换为 DerivationStep 格式
            derivation_steps = []
            for i, (sentential_form, production) in enumerate(raw_steps):
                # 计算替换位置（对于最右推导，找最右边的被替换非终结符）
                position = 0
                if production is not None and i > 0:
                    prev_form = raw_steps[i-1][0]
                    # 找到被替换的非终结符位置（从右到左找）
                    for j in range(len(prev_form) - 1, -1, -1):
                        if prev_form[j] == production.left:
                            position = j
                            break
                derivation_steps.append(DerivationStep(sentential_form, production, position))
            return True, derivation_steps
        
        # 如果通用方法失败，先获取最左推导
        success, leftmost_steps = self.generate_leftmost_derivation(sentence)
        if not success or len(leftmost_steps) < 2:
            return False, []
        
        # 提取使用的产生式列表（按最左推导的顺序）
        productions_used = []
        for step in leftmost_steps[1:]:  # 跳过初始步骤
            if step.production is not None:
                productions_used.append(step.production)
        
        # 使用相同的产生式，但按最右推导的顺序应用
        rightmost_steps = []
        current_form = [self.grammar.start_symbol]
        rightmost_steps.append(DerivationStep(current_form.copy(), None, 0))
        
        # 对于最右推导，我们需要从右到左展开非终结符
        # 使用递归方法构建推导序列
        remaining_prods = productions_used.copy()
        self._apply_rightmost_productions(current_form, remaining_prods, rightmost_steps)
        
        return True, rightmost_steps
    
    def _apply_rightmost_productions(self, current_form: List[str], 
                                      remaining_prods: List[Production], 
                                      steps: List[DerivationStep]):
        """
        递归地应用产生式进行最右推导
        :param current_form: 当前句型
        :param remaining_prods: 剩余的产生式列表
        :param steps: 推导步骤列表（会被修改）
        """
        if not remaining_prods:
            return
        
        # 找到最右的非终结符
        rightmost_pos = -1
        for i in range(len(current_form) - 1, -1, -1):
            if current_form[i] in self.grammar.non_terminals:
                rightmost_pos = i
                break
        
        if rightmost_pos == -1:
            # 没有非终结符了
            return
        
        # 找到可以应用到该非终结符的产生式
        nt_symbol = current_form[rightmost_pos]
        prod_index = -1
        
        for i, prod in enumerate(remaining_prods):
            if prod.left == nt_symbol:
                prod_index = i
                break
        
        if prod_index == -1:
            # 找不到合适的产生式，尝试先展开其他非终结符
            # 递归地向左查找
            if rightmost_pos > 0:
                # 暂时跳过这个非终结符，继续向左找
                for i in range(rightmost_pos - 1, -1, -1):
                    if current_form[i] in self.grammar.non_terminals:
                        # 找到可用的产生式
                        for j, prod in enumerate(remaining_prods):
                            if prod.left == current_form[i]:
                                prod_index = j
                                rightmost_pos = i
                                break
                        if prod_index != -1:
                            break
        
        if prod_index == -1:
            # 仍然找不到，返回
            return
        
        # 应用产生式
        production = remaining_prods[prod_index]
        remaining_prods.pop(prod_index)
        
        # 替换最右非终结符
        new_form = current_form[:rightmost_pos]
        if not production.is_epsilon():
            new_form.extend(production.right)
        new_form.extend(current_form[rightmost_pos + 1:])
        
        steps.append(DerivationStep(new_form.copy(), production, rightmost_pos))
        
        # 递归处理剩余的产生式
        self._apply_rightmost_productions(new_form, remaining_prods, steps)
    
    def print_derivation(self, steps: List[DerivationStep], derivation_type: str = "最左"):
        """
        打印推导过程
        :param steps: 推导步骤列表
        :param derivation_type: 推导类型（"最左"或"最右"）
        """
        self.console.print(f"\n[bold cyan]{derivation_type}推导过程：[/bold cyan]\n")
        
        # 创建表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("步骤", style="cyan", width=6)
        table.add_column("句型", style="yellow")
        table.add_column("使用的产生式", style="green")
        
        # 添加初始步骤
        for i, step in enumerate(steps):
            sentential_form_str = ' '.join(step.sentential_form)
            
            if step.production is None:
                # 初始步骤
                table.add_row(str(i), sentential_form_str, "(起始)")
            else:
                # 查找产生式编号
                prod_index = self.grammar.productions.index(step.production)
                prod_str = f"({prod_index}) {step.production}"
                
                # 高亮显示被替换的符号
                highlighted_form = self._highlight_position(
                    step.sentential_form, 
                    step.position, 
                    len(step.production.right) if not step.production.is_epsilon() else 0
                )
                
                table.add_row(str(i), highlighted_form, prod_str)
        
        self.console.print(table)
        
        # 显示最终句子
        final_form = ' '.join(steps[-1].sentential_form)
        self.console.print(f"\n[bold green]✓ 最终句子：{final_form}[/bold green]")
    
    def _highlight_position(self, sentential_form: List[str], position: int, length: int) -> str:
        """
        高亮显示替换位置
        :param sentential_form: 句型
        :param position: 替换起始位置
        :param length: 替换长度
        :return: 高亮后的字符串
        """
        result = []
        for i, symbol in enumerate(sentential_form):
            if position <= i < position + length:
                result.append(f"[bold red]{symbol}[/bold red]")
            else:
                result.append(symbol)
        return ' '.join(result)
    
    def visualize_parse_tree(self, sentence: List[str], derivation_steps: List[DerivationStep], output_path: str = None):
        """
        可视化语法分析树（从推导步骤构建）
        :param sentence: 句子
        :param derivation_steps: 推导步骤
        :param output_path: 输出路径（不含扩展名）
        """
        if not derivation_steps or len(derivation_steps) < 2:
            self.console.print("[bold yellow]⚠ 推导步骤不足，无法生成语法树[/bold yellow]")
            return
        
        # 从推导步骤构建语法树
        parse_tree = self._build_tree_from_derivation(derivation_steps, sentence)
        
        if parse_tree is None:
            self.console.print("[bold yellow]⚠ 无法构建语法树[/bold yellow]")
            return
        
        # 使用树可视化器
        from src.utils.tree_visualizer import ParseTreeVisualizer
        visualizer = ParseTreeVisualizer()
        
        # 保存图片
        if output_path:
            sentence_str = ' '.join(sentence) if sentence else '(空串)'
            visualizer.visualize(parse_tree, output_path, sentence_str)
            self.console.print(f"\n[bold green]✓ 语法树已保存到：{output_path}.png[/bold green]")
    
    def _build_tree_from_derivation(self, derivation_steps: List[DerivationStep], sentence: List[str]):
        """
        从推导步骤构建语法树
        :param derivation_steps: 推导步骤列表
        :param sentence: 目标句子
        :return: ParseTree 对象
        """
        from src.core.parse_tree import ParseTree, ParseTreeNode
        
        # 创建根节点
        root = ParseTreeNode(self.grammar.start_symbol)
        tree = ParseTree(self.grammar.start_symbol)
        tree.root = root
        
        # 维护一个节点列表，对应当前句型中的每个符号
        # 初始时只有根节点
        current_nodes = [root]
        
        # 跳过初始步骤，从第一个推导开始
        for step in derivation_steps[1:]:
            if step.production is None:
                continue
            
            production = step.production
            position = step.position
            
            # 获取要展开的节点
            if position >= len(current_nodes):
                break
            
            expanding_node = current_nodes[position]
            
            # 验证节点符号与产生式左部匹配
            if expanding_node.symbol != production.left:
                # 理论上不应该发生
                continue
            
            # 为产生式右部的每个符号创建子节点
            new_children_nodes = []
            if production.is_epsilon():
                # epsilon 产生式，创建 ε 节点
                epsilon_node = ParseTreeNode('ε')
                expanding_node.children.append(epsilon_node)
                # epsilon 不会出现在新的节点列表中
            else:
                for symbol in production.right:
                    child = ParseTreeNode(symbol)
                    expanding_node.children.append(child)
                    new_children_nodes.append(child)
            
            # 更新当前节点列表：用新子节点替换被展开的节点
            current_nodes = (
                current_nodes[:position] + 
                new_children_nodes + 
                current_nodes[position + 1:]
            )
        
        return tree
