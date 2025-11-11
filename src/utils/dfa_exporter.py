"""
DFA导出工具
将LR自动机导出为JSON格式
"""

import json
import os
from typing import Dict, List, Any


class DFAExporter:
    """DFA导出器，将LR自动机导出为JSON格式"""
    
    def __init__(self, automaton, algorithm_name: str):
        """
        初始化导出器
        :param automaton: LR自动机对象
        :param algorithm_name: 算法名称（如"LR0", "SLR", "LR1", "LALR1"）
        """
        self.automaton = automaton
        self.algorithm_name = algorithm_name
    
    def export_to_json(self, output_dir: str = "output/dfa_data") -> str:
        """
        导出DFA为JSON格式
        :param output_dir: 输出目录
        :return: 生成的文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建JSON数据
        dfa_data = self._build_dfa_data()
        
        # 生成文件名
        clean_name = self.algorithm_name.lower().replace('(', '').replace(')', '').replace(' ', '')
        filename = f"dfa_{clean_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 写入文件（使用indent=2使JSON更易读）
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dfa_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def _build_dfa_data(self) -> Dict[str, Any]:
        """
        构建DFA的JSON数据结构
        :return: 符合规范的JSON数据
        """
        states_data = []
        
        # 遍历所有状态
        for state in self.automaton.states:
            state_data = {
                "id": state.state_id,
                "items": self._build_items_data(state),
                "transitions": self._build_transitions_data(state.state_id)
            }
            states_data.append(state_data)
        
        return {"states": states_data}
    
    def _build_items_data(self, state) -> List[Dict[str, Any]]:
        """
        构建状态的项集合数据
        :param state: 状态对象
        :return: 项的列表
        """
        items_data = []
        
        for item in state.items:
            # 获取产生式信息
            production = item.production
            lhs = production.left
            rhs = list(production.right) if production.right != ['ε'] else ['ε']
            dot = item.dot_position
            
            # 获取前看符号（如果存在）
            lookahead = []
            if hasattr(item, 'lookahead'):
                # LR(1)和LALR(1)有前看符号
                if isinstance(item.lookahead, set):
                    # LALR可能合并了多个前看符号
                    lookahead = sorted(list(item.lookahead))
                elif item.lookahead is not None:
                    lookahead = [item.lookahead]
            
            # 如果没有前看符号（LR(0)和SLR），使用空列表
            if not lookahead:
                lookahead = []
            
            item_data = {
                "lhs": lhs,
                "rhs": rhs,
                "dot": dot,
                "lookahead": lookahead
            }
            items_data.append(item_data)
        
        return items_data
    
    def _build_transitions_data(self, state_id: int) -> Dict[str, int]:
        """
        构建从该状态出发的转移
        :param state_id: 状态编号
        :return: 转移字典 {符号: 目标状态id}
        """
        transitions = {}
        
        # 遍历所有转移，找到从该状态出发的
        for (from_id, symbol), to_id in self.automaton.transitions.items():
            if from_id == state_id:
                transitions[symbol] = to_id
        
        return transitions
    
    @staticmethod
    def load_from_json(filepath: str) -> Dict[str, Any]:
        """
        从JSON文件加载DFA数据
        :param filepath: JSON文件路径
        :return: DFA数据
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def validate_format(data: Dict[str, Any]) -> bool:
        """
        验证JSON数据是否符合DFA格式规范
        :param data: 待验证的数据
        :return: 是否符合规范
        """
        try:
            # 检查顶层结构
            if not isinstance(data, dict) or "states" not in data:
                return False
            
            states = data["states"]
            if not isinstance(states, list):
                return False
            
            # 检查每个状态
            for state in states:
                if not isinstance(state, dict):
                    return False
                
                # 检查必需字段
                if "id" not in state or "items" not in state or "transitions" not in state:
                    return False
                
                # 检查id是整数
                if not isinstance(state["id"], int):
                    return False
                
                # 检查items是列表
                if not isinstance(state["items"], list):
                    return False
                
                # 检查每个item
                for item in state["items"]:
                    if not isinstance(item, dict):
                        return False
                    
                    required_fields = ["lhs", "rhs", "dot", "lookahead"]
                    if not all(field in item for field in required_fields):
                        return False
                    
                    if not isinstance(item["lhs"], str):
                        return False
                    if not isinstance(item["rhs"], list):
                        return False
                    if not isinstance(item["dot"], int):
                        return False
                    if not isinstance(item["lookahead"], list):
                        return False
                
                # 检查transitions是字典
                if not isinstance(state["transitions"], dict):
                    return False
                
                # 检查transitions的值都是整数
                for target in state["transitions"].values():
                    if not isinstance(target, int):
                        return False
            
            return True
        
        except Exception:
            return False
