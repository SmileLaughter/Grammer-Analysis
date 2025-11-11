"""
文法解析模块
从文件中读取文法并解析
"""

from src.core.grammar import Grammar
from typing import List


class GrammarParser:
    """文法解析器类"""
    
    @staticmethod
    def parse_from_file(filename: str) -> Grammar:
        """
        从文件中解析文法
        :param filename: 文法文件路径
        :return: Grammar对象
        """
        grammar = Grammar()
        
        # 读取文件内容（使用 utf-8-sig 自动处理 BOM）
        with open(filename, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # 解析每一行
        for line in lines:
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析产生式
            GrammarParser._parse_production_line(line, grammar)
        
        return grammar
    
    @staticmethod
    def parse_from_lines(lines: List[str]) -> Grammar:
        """
        从字符串列表解析文法
        :param lines: 文法行列表
        :return: Grammar对象
        """
        grammar = Grammar()
        
        # 解析每一行
        for i, line in enumerate(lines):
            # 处理第一行可能的 BOM
            if i == 0 and line.startswith('\ufeff'):
                line = line[1:]
            
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析产生式
            GrammarParser._parse_production_line(line, grammar)
        
        return grammar
    
    @staticmethod
    def _parse_production_line(line: str, grammar: Grammar):
        """
        解析单行产生式
        格式：A : alpha | beta | gamma 或 A -> alpha | beta | gamma
        :param line: 产生式行
        :param grammar: 文法对象
        """
        # 再次检查是否为注释或空行（防止strip后的问题）
        if not line or line.startswith('#'):
            return
        
        # 分割左部和右部（支持 '->' 或 ':' 分隔）
        separator = None
        if '->' in line:
            separator = '->'
        elif ':' in line:
            separator = ':'
        else:
            raise ValueError(f"产生式格式错误（缺少 ':' 或 '->'）: {line}")
        
        parts = line.split(separator, 1)
        left = parts[0].strip()  # 左部非终结符
        right_part = parts[1].strip()  # 右部
        
        # 检查左部是否为非终结符（大写字母或大写字母+单引号）
        if not left or not (left[0].isupper() and all(c.isupper() or c == "'" for c in left)):
            raise ValueError(f"产生式左部必须是大写字母或大写字母+单引号: {line}")
        
        # 处理右部的多个候选式（使用|分隔）
        alternatives = right_part.split('|')
        
        # 为每个候选式创建一个产生式
        for alternative in alternatives:
            alternative = alternative.strip()
            
            # 解析右部符号
            if alternative == 'ε' or alternative == '':
                # epsilon产生式
                symbols = []
            else:
                # 将右部分割成符号列表（按空格分割）
                symbols = GrammarParser._parse_symbols(alternative)
            
            # 添加产生式到文法
            grammar.add_production(left, symbols)
    
    @staticmethod
    def _parse_symbols(text: str) -> List[str]:
        """
        解析符号串，支持 prime 标记（如 S', A' 等）
        :param text: 符号串文本
        :return: 符号列表
        """
        text = text.strip()
        
        # 优先按空格分割
        if ' ' in text:
            return text.split()
        
        # 如果没有空格，检查是否全部是小写字母（如 id, num 等）
        # 或者全部是同一类字符，则作为单个符号
        if text.islower() or text.isdigit():
            return [text]
        
        # 否则需要智能分割，识别 S' 这样的非终结符
        symbols = []
        i = 0
        while i < len(text):
            # 检查是否是大写字母开头
            if text[i].isupper():
                # 收集大写字母和后续的单引号
                symbol = text[i]
                i += 1
                # 收集所有连续的单引号
                while i < len(text) and text[i] == "'":
                    symbol += text[i]
                    i += 1
                symbols.append(symbol)
            else:
                # 其他字符作为单独的符号
                symbols.append(text[i])
                i += 1
        
        return symbols


class SentenceParser:
    """句子解析器类"""
    
    @staticmethod
    def parse_from_file(filename: str) -> List[str]:
        """
        从文件中读取待解析的句子
        :param filename: 句子文件路径
        :return: 符号列表
        """
        # 使用 utf-8-sig 自动处理 BOM
        with open(filename, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
        
        # 如果句子为空，返回空列表
        if not content:
            return []
        
        # 按空格分割，如果没有空格则按字符分割
        if ' ' in content:
            return content.split()
        else:
            return list(content)
