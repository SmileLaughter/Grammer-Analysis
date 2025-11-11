# prompt 1
在文件夹Chp 3 Grammer analysis里面，使用python语言，帮我编写语法分析算法的代码。要求如下：
1. 从 input 文件夹中的某个文件输入文法，其中大写字母代表非终结符，小写字母代表终结符，| 代表左部相同的产生式，: 冒号用于分隔产生式的左部和右部。
文法示例：
S : aAB | bBC
A  : aA | ε
B : bB | c
C : cC | d
2. 从 input 文件夹中的某个文件输入需要解析的句子
3. 根据输入的文法，求解如下内容，求解顺序你自己决定：
  a. 每个非终结符的 FIRST 集（基于 NULLABLE集、FOLLOW 集的改进版本）
  b. 每个产生式的 FIRST 集（基于 NULLABLE集、FOLLOW 集的改进版本）
  c. NULLABLE 集
  d. 每个非终结符的 FOLLOW 集
对于上述的每个集合，都以表格的形式输出，行代表非终结符或者产生式，列代表对应的集合。
4. 能够通过输入，指定使用哪一个算法进行语法分析。
5. 根据上述求解出来的集合，实现 LL(1)分析算法，并输出 LL(1)分析表（如果输入指定使用 LL(1)分析算法）。
6. 之后我还需要你实现其他的语法分析算法，你记得保留扩展接口
7. 使用 rich 库美化终端的输出（如表格等等）

# prompt 2
现在实现 LR(0),SLR 算法，合并到之前的语法分析项目的逻辑中
要求能够根据输出选择使用 LR(0)或者 SLR 算法
能够输出构造的 DFA、LR(0)分析表、以及文法和句子的匹配过程
LR(0)分析表示例（这里使用 html，你可以根据 rich 库的用法自行决定输出样式，能够体现列的合并效果即可）：
<table border="1" cellpadding="6" cellspacing="0">
  <thead>
    <tr>
      <th rowspan="2">状态</th>
      <th colspan="3">动作 (ACTION)</th>
      <th colspan="2">转移 (GOTO)</th>
    </tr>
    <tr>
      <th>x</th>
      <th>y</th>
      <th>$</th>
      <th>S</th>
      <th>T</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>s2</td>
      <td></td>
      <td></td>
      <td>g6</td>
      <td></td>
    </tr>
    <tr>
      <td>2</td>
      <td>s3</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>3</td>
      <td></td>
      <td>s4</td>
      <td></td>
      <td></td>
      <td>g5</td>
    </tr>
    <tr>
      <td>4</td>
      <td>r2</td>
      <td>r2</td>
      <td>r2</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>5</td>
      <td>r1</td>
      <td>r1</td>
      <td>r1</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>6</td>
      <td></td>
      <td></td>
      <td>accept</td>
      <td></td>
      <td></td>
    </tr>
  </tbody>
</table>

# prompt 3
现在实现 LR1, LALR1 算法，合并到之前的语法分析的项目逻辑中，要求如下：
1. 引入前看记号，并体现在 DFA 中
2. 对于这两个算法，均输出 DFA 和最终的分析表，格式与之前相同