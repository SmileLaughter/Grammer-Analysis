"""
语法分析树可视化工具
使用 graphviz 绘制语法树
"""

import os
from typing import Optional
from src.core.parse_tree import ParseTree, ParseTreeNode

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


class ParseTreeVisualizer:
    """语法分析树可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        self.node_counter = 0
        self.node_ids = {}  # 节点到ID的映射
    
    def visualize(self, tree: ParseTree, output_path: str, sentence: str = ""):
        """
        可视化语法树并保存为图片
        :param tree: 语法树
        :param output_path: 输出路径（不含扩展名）
        :param sentence: 句子（用于标题）
        """
        if not GRAPHVIZ_AVAILABLE:
            print("警告: graphviz 未安装，无法生成语法树图片")
            print("  请运行: pip install graphviz")
            return False
        
        # 创建有向图
        dot = graphviz.Digraph(comment='Parse Tree')
        dot.attr(rankdir='TB')  # 从上到下布局
        dot.attr('node', shape='circle', style='filled')
        
        # 设置图的属性 - 使用英文避免编码问题
        if sentence:
            dot.attr(label=f'Parse Tree\\nSentence: {sentence}')
            dot.attr(fontsize='16')
            dot.attr(labelloc='t')
        
        # 重置节点计数器
        self.node_counter = 0
        self.node_ids = {}
        
        # 递归添加节点和边
        self._add_nodes_and_edges(dot, tree.get_root())
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存图片
        try:
            dot.render(output_path, format='png', cleanup=True)
            print(f"语法树图片已保存到: {output_path}.png")
            return True
        except Exception as e:
            print(f"保存语法树图片失败: {e}")
            return False
    
    def _add_nodes_and_edges(self, dot: graphviz.Digraph, node: ParseTreeNode):
        """
        递归添加节点和边
        :param dot: graphviz 图对象
        :param node: 当前节点
        """
        # 为当前节点分配唯一ID
        if node not in self.node_ids:
            node_id = f"node_{self.node_counter}"
            self.node_ids[node] = node_id
            self.node_counter += 1
            
            # 添加节点
            if node.is_terminal:
                # 终结符：使用方框，填充颜色
                dot.node(node_id, node.symbol, 
                        shape='box', 
                        fillcolor='lightblue',
                        style='filled')
            else:
                # 非终结符：使用圆形，填充颜色
                dot.node(node_id, node.symbol, 
                        shape='circle', 
                        fillcolor='lightgreen',
                        style='filled')
        
        current_id = self.node_ids[node]
        
        # 递归处理子节点
        for child in node.children:
            # 为子节点分配ID
            if child not in self.node_ids:
                child_id = f"node_{self.node_counter}"
                self.node_ids[child] = child_id
                self.node_counter += 1
                
                # 添加子节点
                if child.is_terminal:
                    dot.node(child_id, child.symbol, 
                            shape='box', 
                            fillcolor='lightblue',
                            style='filled')
                else:
                    dot.node(child_id, child.symbol, 
                            shape='circle', 
                            fillcolor='lightgreen',
                            style='filled')
            
            child_id = self.node_ids[child]
            
            # 添加边
            dot.edge(current_id, child_id)
            
            # 递归处理子节点的子节点
            if not child.is_leaf():
                self._add_nodes_and_edges(dot, child)
    
    def print_tree_structure(self, tree: ParseTree):
        """
        打印树的结构到控制台
        :param tree: 语法树
        """
        print("\n" + "=" * 60)
        print("语法分析树结构")
        print("=" * 60)
        tree.print_tree()
        
        # 打印节点关系
        print("\n" + "=" * 60)
        print("节点关系")
        print("=" * 60)
        relations = tree.get_nodes_relations()
        for parent, child in relations:
            print(f"  {parent.symbol} -> {child.symbol}")
        
        # 打印叶子节点序列
        print("\n" + "=" * 60)
        print("叶子节点序列")
        print("=" * 60)
        leaves = tree.get_leaves()
        leaf_symbols = [leaf.symbol for leaf in leaves]
        print(f"  {' '.join(leaf_symbols)}")
