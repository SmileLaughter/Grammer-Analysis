"""
DFA同构验证程序
验证多个基于LR算法生成的DFA是否同构
"""

import os
import json
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class DFAComparator:
    """DFA比较器，用于验证DFA同构性"""
    
    def __init__(self):
        """初始化比较器"""
        self.console = Console()
    
    def find_dfa_files(self, root_dir: str = ".") -> List[str]:
        """
        递归查找所有包含'dfa'的JSON文件
        :param root_dir: 根目录
        :return: 符合格式的DFA文件路径列表
        """
        dfa_files = []
        
        # 递归遍历目录
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                # 检查文件名是否包含'dfa'且为json文件
                if 'dfa' in file.lower() and file.endswith('.json'):
                    filepath = os.path.join(root, file)
                    
                    # 验证文件格式
                    if self._validate_dfa_file(filepath):
                        dfa_files.append(filepath)
        
        return sorted(dfa_files)
    
    def _validate_dfa_file(self, filepath: str) -> bool:
        """
        验证文件是否为有效的DFA格式
        :param filepath: 文件路径
        :return: 是否有效
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查顶层结构
            if not isinstance(data, dict) or "states" not in data:
                return False
            
            states = data["states"]
            if not isinstance(states, list) or len(states) == 0:
                return False
            
            # 检查每个状态的基本结构
            for state in states:
                if not isinstance(state, dict):
                    return False
                
                required_fields = ["id", "items", "transitions"]
                if not all(field in state for field in required_fields):
                    return False
                
                # 检查items
                if not isinstance(state["items"], list):
                    return False
                
                for item in state["items"]:
                    if not isinstance(item, dict):
                        return False
                    
                    item_fields = ["lhs", "rhs", "dot", "lookahead"]
                    if not all(field in item for field in item_fields):
                        return False
            
            return True
        
        except Exception:
            return False
    
    def load_dfa(self, filepath: str) -> Dict[str, Any]:
        """
        加载DFA数据
        :param filepath: 文件路径
        :return: DFA数据
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def compare_dfas(self, dfa_files: List[str]) -> Dict[str, Any]:
        """
        比较多个DFA，检查是否同构
        :param dfa_files: DFA文件路径列表
        :return: 比较结果
        """
        if len(dfa_files) < 2:
            return {
                "error": "至少需要两个DFA文件才能进行比较"
            }
        
        # 加载所有DFA
        dfas = []
        for filepath in dfa_files:
            dfa = self.load_dfa(filepath)
            dfas.append({
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "data": dfa
            })
        
        # 比较结果
        results = {
            "files": [dfa["filename"] for dfa in dfas],
            "state_counts": {},
            "isomorphic": True,
            "differences": []
        }
        
        # 1. 比较状态数量
        for dfa in dfas:
            filename = dfa["filename"]
            state_count = len(dfa["data"]["states"])
            results["state_counts"][filename] = state_count
        
        # 检查状态数量是否一致
        state_counts = list(results["state_counts"].values())
        if len(set(state_counts)) > 1:
            results["isomorphic"] = False
            results["differences"].append({
                "type": "state_count",
                "description": "状态数量不一致",
                "details": results["state_counts"]
            })
        
        # 2. 如果状态数量一致，进行更详细的比较
        if results["isomorphic"]:
            # 以第一个DFA为基准
            base_dfa = dfas[0]
            
            for i in range(1, len(dfas)):
                compare_dfa = dfas[i]
                
                # 尝试找到状态映射
                mapping = self._find_state_mapping(
                    base_dfa["data"],
                    compare_dfa["data"]
                )
                
                if mapping is None:
                    results["isomorphic"] = False
                    results["differences"].append({
                        "type": "structure",
                        "description": f"{base_dfa['filename']} 和 {compare_dfa['filename']} 的结构不同",
                        "details": "无法找到有效的状态映射"
                    })
                else:
                    # 比较具体差异
                    diffs = self._compare_with_mapping(
                        base_dfa["data"],
                        compare_dfa["data"],
                        mapping,
                        base_dfa["filename"],
                        compare_dfa["filename"]
                    )
                    
                    if diffs:
                        results["isomorphic"] = False
                        results["differences"].extend(diffs)
        
        return results
    
    def _find_state_mapping(self, dfa1: Dict, dfa2: Dict) -> Optional[Dict[int, int]]:
        """
        尝试找到两个DFA之间的状态映射
        使用BFS从起始状态开始匹配
        :param dfa1: 第一个DFA
        :param dfa2: 第二个DFA
        :return: 状态映射字典 {dfa1_state_id: dfa2_state_id}，失败返回None
        """
        # 构建状态字典（按ID索引）
        states1 = {state["id"]: state for state in dfa1["states"]}
        states2 = {state["id"]: state for state in dfa2["states"]}
        
        # 找到起始状态（假设是ID最小的状态）
        start1 = min(states1.keys())
        start2 = min(states2.keys())
        
        # BFS匹配
        mapping = {start1: start2}
        queue = [(start1, start2)]
        visited = {start1}
        
        while queue:
            id1, id2 = queue.pop(0)
            state1 = states1[id1]
            state2 = states2[id2]
            
            # 检查项集合是否匹配（忽略前看符号的差异）
            if not self._items_match_structure(state1["items"], state2["items"]):
                return None
            
            # 检查转移
            trans1 = state1["transitions"]
            trans2 = state2["transitions"]
            
            # 转移的符号必须一致
            if set(trans1.keys()) != set(trans2.keys()):
                return None
            
            # 对每个符号的转移进行映射
            for symbol in trans1.keys():
                target1 = trans1[symbol]
                target2 = trans2[symbol]
                
                if target1 in mapping:
                    # 已有映射，检查是否一致
                    if mapping[target1] != target2:
                        return None
                else:
                    # 建立新映射
                    mapping[target1] = target2
                    if target1 not in visited:
                        visited.add(target1)
                        queue.append((target1, target2))
        
        return mapping
    
    def _items_match_structure(self, items1: List[Dict], items2: List[Dict]) -> bool:
        """
        检查两个项集合的结构是否匹配（忽略前看符号）
        :param items1: 第一个项集合
        :param items2: 第二个项集合
        :return: 是否匹配
        """
        # 提取项的核心（lhs, rhs, dot）
        cores1 = {self._item_core_str(item) for item in items1}
        cores2 = {self._item_core_str(item) for item in items2}
        
        return cores1 == cores2
    
    def _item_core_str(self, item: Dict) -> str:
        """
        获取项的核心字符串表示（不包括前看符号）
        :param item: 项
        :return: 核心字符串
        """
        return f"{item['lhs']} -> {' '.join(item['rhs'])} @ {item['dot']}"
    
    def _compare_with_mapping(
        self,
        dfa1: Dict,
        dfa2: Dict,
        mapping: Dict[int, int],
        name1: str,
        name2: str
    ) -> List[Dict[str, Any]]:
        """
        根据状态映射比较两个DFA的详细差异
        :param dfa1: 第一个DFA
        :param dfa2: 第二个DFA
        :param mapping: 状态映射
        :param name1: 第一个DFA名称
        :param name2: 第二个DFA名称
        :return: 差异列表
        """
        differences = []
        
        states1 = {state["id"]: state for state in dfa1["states"]}
        states2 = {state["id"]: state for state in dfa2["states"]}
        
        # 比较每对映射的状态
        for id1, id2 in mapping.items():
            state1 = states1[id1]
            state2 = states2[id2]
            
            # 比较前看符号
            lookahead_diffs = self._compare_lookaheads(state1["items"], state2["items"])
            if lookahead_diffs:
                differences.append({
                    "type": "lookahead",
                    "description": f"状态 {id1}({name1}) 和 {id2}({name2}) 的前看符号不同",
                    "state1": id1,
                    "state2": id2,
                    "details": lookahead_diffs
                })
        
        return differences
    
    def _compare_lookaheads(self, items1: List[Dict], items2: List[Dict]) -> List[str]:
        """
        比较两个项集合的前看符号差异
        :param items1: 第一个项集合
        :param items2: 第二个项集合
        :return: 差异描述列表
        """
        differences = []
        
        # 按核心分组
        core_to_lookahead1 = {}
        for item in items1:
            core = self._item_core_str(item)
            if core not in core_to_lookahead1:
                core_to_lookahead1[core] = set()
            core_to_lookahead1[core].update(item["lookahead"])
        
        core_to_lookahead2 = {}
        for item in items2:
            core = self._item_core_str(item)
            if core not in core_to_lookahead2:
                core_to_lookahead2[core] = set()
            core_to_lookahead2[core].update(item["lookahead"])
        
        # 比较每个核心的前看符号
        all_cores = set(core_to_lookahead1.keys()) | set(core_to_lookahead2.keys())
        
        for core in all_cores:
            lookahead1 = core_to_lookahead1.get(core, set())
            lookahead2 = core_to_lookahead2.get(core, set())
            
            if lookahead1 != lookahead2:
                only_in_1 = lookahead1 - lookahead2
                only_in_2 = lookahead2 - lookahead1
                
                diff_msg = f"项 [{core}]:"
                if only_in_1:
                    diff_msg += f" 仅在DFA1中: {sorted(only_in_1)}"
                if only_in_2:
                    diff_msg += f" 仅在DFA2中: {sorted(only_in_2)}"
                
                differences.append(diff_msg)
        
        return differences
    
    def print_comparison_results(self, results: Dict[str, Any]):
        """
        打印比较结果
        :param results: 比较结果
        """
        self.console.print("\n" + "="*70)
        self.console.print("[bold cyan]DFA同构验证结果[/bold cyan]")
        self.console.print("="*70 + "\n")
        
        # 显示被比较的文件
        self.console.print("[bold]被比较的DFA文件：[/bold]")
        for i, filename in enumerate(results["files"], 1):
            self.console.print(f"  {i}. {filename}")
        
        # 显示状态数量
        self.console.print("\n[bold]状态数量：[/bold]")
        table = Table(box=box.SIMPLE)
        table.add_column("文件名", style="cyan")
        table.add_column("状态数", justify="right", style="yellow")
        
        for filename, count in results["state_counts"].items():
            table.add_row(filename, str(count))
        
        self.console.print(table)
        
        # 显示同构性结果
        if results["isomorphic"]:
            self.console.print("\n[bold green]✓ 所有DFA同构！[/bold green]")
        else:
            self.console.print("\n[bold red]✗ DFA不同构[/bold red]")
            
            # 显示差异
            if results["differences"]:
                self.console.print("\n[bold]发现的差异：[/bold]")
                
                for i, diff in enumerate(results["differences"], 1):
                    self.console.print(f"\n[yellow]{i}. {diff['description']}[/yellow]")
                    
                    if diff["type"] == "state_count":
                        for filename, count in diff["details"].items():
                            self.console.print(f"   - {filename}: {count} 个状态")
                    
                    elif diff["type"] == "structure":
                        self.console.print(f"   {diff['details']}")
                    
                    elif diff["type"] == "lookahead":
                        self.console.print(f"   状态映射: {diff['state1']} <-> {diff['state2']}")
                        for detail in diff["details"]:
                            self.console.print(f"   {detail}")
        
        self.console.print("\n" + "="*70)


def main():
    """主程序"""
    from rich.prompt import Prompt
    from rich.panel import Panel
    
    comparator = DFAComparator()
    console = Console()
    
    # 显示标题
    title = Panel(
        "[bold cyan]DFA同构验证程序[/bold cyan]\n\n"
        "自动搜索并比较DFA文件的同构性",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(title)
    
    # 显示算法选择菜单
    console.print("\n[bold yellow]请选择要检查的算法：[/bold yellow]\n")
    
    menu_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    menu_table.add_column("选项", style="cyan", justify="right")
    menu_table.add_column("算法名称", style="green")
    
    menu_table.add_row("[0]", "所有算法")
    menu_table.add_row("[1]", "LR(0)")
    menu_table.add_row("[2]", "SLR")
    menu_table.add_row("[3]", "LR(1)")
    menu_table.add_row("[4]", "LALR(1)")
    
    console.print(menu_table)
    
    # 获取用户选择
    choice = Prompt.ask(
        "\n请输入选项编号",
        choices=["0", "1", "2", "3", "4"],
        default="0"
    )
    
    # 根据选择确定算法过滤器
    algorithm_filter = None
    algorithm_names = {
        "0": "所有算法",
        "1": "LR(0)",
        "2": "SLR",
        "3": "LR(1)",
        "4": "LALR(1)"
    }
    
    selected_algorithm = algorithm_names[choice]
    
    if choice != "0":
        # 设置过滤器（转换为搜索关键字）
        # 注意：使用更精确的模式匹配避免误匹配（如lr1包含在lalr1中）
        filter_patterns = {
            "1": ["lr0"],           # 只匹配lr0
            "2": ["slr"],           # 只匹配slr
            "3": ["lr1"],           # 匹配lr1但排除lalr1
            "4": ["lalr"]           # 只匹配lalr
        }
        algorithm_filter = filter_patterns[choice]
        console.print(f"\n[cyan]✓ 已选择: {selected_algorithm}[/cyan]")
    else:
        console.print(f"\n[cyan]✓ 已选择: {selected_algorithm}[/cyan]")
    
    # 查找DFA文件
    console.print("\n正在搜索DFA文件...")
    dfa_files = comparator.find_dfa_files()
    
    if not dfa_files:
        console.print("[red]未找到任何有效的DFA文件[/red]")
        return
    
    # 应用算法过滤器
    if algorithm_filter:
        original_count = len(dfa_files)
        filtered_files = []
        
        for f in dfa_files:
            filename_lower = os.path.basename(f).lower()
            # 检查是否包含所需的模式
            match = False
            for pattern in algorithm_filter:
                if pattern in filename_lower:
                    # 对于lr1，需要排除lalr1
                    if pattern == "lr1" and "lalr" in filename_lower:
                        continue
                    match = True
                    break
            if match:
                filtered_files.append(f)
        
        dfa_files = filtered_files
        console.print(f"过滤后: {len(dfa_files)}/{original_count} 个文件")
    
    if not dfa_files:
        console.print(f"[red]未找到 {selected_algorithm} 的DFA文件[/red]")
        return
    
    console.print(f"\n找到 {len(dfa_files)} 个 {selected_algorithm} 的DFA文件：")
    for i, filepath in enumerate(dfa_files, 1):
        console.print(f"  {i}. [cyan]{os.path.basename(filepath)}[/cyan] - {filepath}")
    
    if len(dfa_files) < 2:
        console.print("\n[yellow]至少需要2个DFA文件才能进行比较[/yellow]")
        return
    
    # 进行比较
    console.print("\n[yellow]开始比较...[/yellow]")
    results = comparator.compare_dfas(dfa_files)
    
    # 显示结果
    comparator.print_comparison_results(results)


if __name__ == "__main__":
    main()
