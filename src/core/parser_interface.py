"""
语法分析器接口模块
定义统一的分析器接口，方便后续扩展其他算法
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from src.core.grammar import Grammar


class ParserInterface(ABC):
    """语法分析器抽象基类"""
    
    def __init__(self, grammar: Grammar):
        """
        初始化分析器
        :param grammar: 文法对象
        """
        self.grammar = grammar
    
    @abstractmethod
    def build(self) -> bool:
        """
        构建分析器（如分析表等）
        :return: 是否构建成功
        """
        pass
    
    @abstractmethod
    def parse(self, sentence: List[str]) -> Tuple[bool, Any]:
        """
        解析句子
        :param sentence: 待解析的句子（符号列表）
        :return: (是否解析成功, 分析过程详细信息)
        """
        pass
    
    @abstractmethod
    def print_table(self):
        """打印分析表"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        获取分析器名称
        :return: 分析器名称
        """
        pass
