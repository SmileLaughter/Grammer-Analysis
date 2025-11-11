"""
语法分析树（Parse Tree）数据结构
用于表示语法分析过程中的推导树
"""

from typing import List, Optional
from src.core.grammar import Production


class ParseTreeNode:
    """
    语法树节点
    内部节点：非终结符
    叶子节点：终结符
    """
    
    def __init__(self, symbol: str, is_terminal: bool = False):
        """
        初始化节点
        :param symbol: 符号（终结符或非终结符）
        :param is_terminal: 是否是终结符
        """
        self.symbol = symbol
        self.is_terminal = is_terminal
        self.children: List['ParseTreeNode'] = []
        self.production: Optional[Production] = None  # 用于生成此节点的产生式
    
    def add_child(self, child: 'ParseTreeNode'):
        """添加子节点"""
        self.children.append(child)
    
    def is_leaf(self) -> bool:
        """判断是否是叶子节点"""
        return len(self.children) == 0
    
    def __str__(self):
        """字符串表示"""
        return f"{'T' if self.is_terminal else 'NT'}:{self.symbol}"
    
    def __repr__(self):
        return self.__str__()


class ParseTree:
    """
    语法分析树
    记录完整的推导过程
    """
    
    def __init__(self, root_symbol: str):
        """
        初始化语法树
        :param root_symbol: 根节点符号（开始符号）
        """
        self.root = ParseTreeNode(root_symbol, is_terminal=False)
    
    def get_root(self) -> ParseTreeNode:
        """获取根节点"""
        return self.root
    
    def print_tree(self, node: Optional[ParseTreeNode] = None, prefix: str = "", is_last: bool = True):
        """
        以树形结构打印语法树
        :param node: 当前节点
        :param prefix: 前缀字符串
        :param is_last: 是否是最后一个子节点
        """
        if node is None:
            node = self.root
        
        # 打印当前节点
        connector = "└── " if is_last else "├── "
        print(prefix + connector + str(node))
        
        # 递归打印子节点
        if not node.is_leaf():
            extension = "    " if is_last else "│   "
            for i, child in enumerate(node.children):
                is_last_child = (i == len(node.children) - 1)
                self.print_tree(child, prefix + extension, is_last_child)
    
    def get_nodes_relations(self) -> List[tuple]:
        """
        获取所有节点之间的关系
        :return: [(父节点, 子节点), ...]
        """
        relations = []
        
        def traverse(node: ParseTreeNode):
            for child in node.children:
                relations.append((node, child))
                traverse(child)
        
        traverse(self.root)
        return relations
    
    def get_all_nodes(self) -> List[ParseTreeNode]:
        """
        获取所有节点（层序遍历）
        :return: 节点列表
        """
        nodes = []
        queue = [self.root]
        
        while queue:
            node = queue.pop(0)
            nodes.append(node)
            queue.extend(node.children)
        
        return nodes
    
    def get_leaves(self) -> List[ParseTreeNode]:
        """
        获取所有叶子节点（从左到右）
        :return: 叶子节点列表
        """
        leaves = []
        
        def traverse(node: ParseTreeNode):
            if node.is_leaf():
                leaves.append(node)
            else:
                for child in node.children:
                    traverse(child)
        
        traverse(self.root)
        return leaves
    
    def get_sentence(self) -> str:
        """
        获取叶子节点组成的句子
        :return: 句子字符串
        """
        leaves = self.get_leaves()
        # 过滤掉 epsilon（ε）和结束符 $
        symbols = [leaf.symbol for leaf in leaves if leaf.symbol not in ['ε', '$', 'ε']]
        return ' '.join(symbols)
