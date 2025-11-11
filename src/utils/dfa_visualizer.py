"""
LR 自动机（DFA）可视化工具
"""

import os
from graphviz import Digraph
from typing import Optional


class LRDFAVisualizer:
    """LR 自动机可视化器"""
    
    def __init__(self, automaton, parser_name: str):
        """
        初始化可视化器
        :param automaton: LR自动机对象（包含states和transitions）
        :param parser_name: 分析器名称（如"LR0", "SLR", "LR1", "LALR"）
        """
        self.automaton = automaton
        self.parser_name = parser_name
    
    def visualize(self, output_dir: str = "output/DFA", filename: Optional[str] = None) -> str:
        """
        生成DFA图片
        :param output_dir: 输出目录
        :param filename: 输出文件名（不含扩展名），默认为"parser_name_dfa"
        :return: 生成的图片路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 默认文件名，移除括号和空格
        if filename is None:
            # 将"LR(0)"转为"lr0", "LR(1)"转为"lr1", "LALR(1)"转为"lalr"等
            clean_name = self.parser_name.lower().replace('(', '').replace(')', '').replace(' ', '')
            filename = f"{clean_name}_dfa"
        
        # 创建Digraph对象
        dot = Digraph(comment=f'{self.parser_name} DFA')
        dot.attr(rankdir='LR')  # 从左到右排列
        dot.attr('node', shape='box', style='rounded', fontname='Microsoft YaHei')
        dot.attr('edge', fontname='Microsoft YaHei')
        
        # 添加初始状态标记（一个不可见的起始节点，指向状态1）
        dot.node('start', '', shape='point')
        dot.edge('start', '1', label='')
        
        # 添加所有状态节点
        for state in self.automaton.states:
            # 格式化项集内容
            items_text = self._format_items(state.items)
            
            # 判断是否为接受状态（包含S' -> S·的项）
            is_accept = self._is_accept_state(state)
            
            # 设置节点样式
            if is_accept:
                dot.node(
                    str(state.state_id),
                    f'I{state.state_id}\n{items_text}',
                    shape='box',
                    style='rounded,filled',
                    fillcolor='lightgreen',
                    fontsize='10'
                )
            else:
                dot.node(
                    str(state.state_id),
                    f'I{state.state_id}\n{items_text}',
                    shape='box',
                    style='rounded',
                    fontsize='10'
                )
        
        # 添加所有转移边
        for (state_id, symbol), target_id in self.automaton.transitions.items():
            dot.edge(
                str(state_id),
                str(target_id),
                label=symbol,
                fontsize='9'
            )
        
        # 保存图片
        output_path = os.path.join(output_dir, filename)
        dot.render(output_path, format='png', cleanup=True)
        
        return f"{output_path}.png"
    
    def _format_items(self, items) -> str:
        """
        格式化项集，显示所有项
        对于LR(1)项，合并具有相同核心但不同前看符号的项
        :param items: 项集
        :return: 格式化后的字符串
        """
        # 对于LR(1)项，按核心（产生式+点位置）分组
        if items and hasattr(next(iter(items)), 'lookahead'):
            # 按核心分组，收集所有前看符号
            core_dict = {}  # (production, dot_position) -> [lookaheads]
            for item in items:
                core = (item.production.index, item.dot_position)
                if core not in core_dict:
                    core_dict[core] = {'item': item, 'lookaheads': []}
                if item.lookahead is not None:
                    core_dict[core]['lookaheads'].append(item.lookahead)
            
            # 按产生式编号和点位置排序
            sorted_cores = sorted(core_dict.items(), key=lambda x: x[0])
            
            # 显示所有项，不限制数量
            return '\n'.join(
                self._format_item_with_lookaheads(data['item'], data['lookaheads'])
                for core, data in sorted_cores
            )
        else:
            # LR(0)项，直接显示所有项
            sorted_items = sorted(items, key=lambda x: (x.production.index, x.dot_position))
            return '\n'.join(self._format_item(item) for item in sorted_items)
    
    def _format_item(self, item) -> str:
        """
        格式化单个项
        :param item: 项对象
        :return: 格式化后的字符串（如"A → α·β"）
        """
        prod = item.production
        left = prod.left
        right = list(prod.right) if prod.right != ['ε'] else []
        
        # 在点的位置插入·
        right_with_dot = right[:item.dot_position] + ['·'] + right[item.dot_position:]
        right_str = ' '.join(right_with_dot) if right_with_dot else '·'
        
        # 对于LR(1)项，还要显示向前看符号
        if hasattr(item, 'lookahead') and item.lookahead is not None:
            return f"{left} → {right_str}, {item.lookahead}"
        else:
            return f"{left} → {right_str}"
    
    def _format_item_with_lookaheads(self, item, lookaheads: list) -> str:
        """
        格式化带有多个前看符号的项（合并显示）
        :param item: 项对象
        :param lookaheads: 前看符号列表
        :return: 格式化后的字符串（如"A → α·β, {a,b,c}"）
        """
        prod = item.production
        left = prod.left
        right = list(prod.right) if prod.right != ['ε'] else []
        
        # 在点的位置插入·
        right_with_dot = right[:item.dot_position] + ['·'] + right[item.dot_position:]
        right_str = ' '.join(right_with_dot) if right_with_dot else '·'
        
        # 合并前看符号
        if lookaheads:
            # 去重并排序
            unique_lookaheads = sorted(set(lookaheads))
            if len(unique_lookaheads) == 1:
                lookahead_str = unique_lookaheads[0]
            else:
                # 使用逗号分隔多个前看符号
                lookahead_str = '{' + ','.join(unique_lookaheads) + '}'
            return f"{left} → {right_str}, {lookahead_str}"
        else:
            return f"{left} → {right_str}"
    
    def _is_accept_state(self, state) -> bool:
        """
        判断是否为接受状态（包含S' -> S·的项）
        :param state: 状态对象
        :return: 是否为接受状态
        """
        for item in state.items:
            # 检查是否为增广文法的规约项（S' -> S·）
            if item.production.left.endswith("'") and item.is_reducible():
                return True
        return False
