"""Build the reviewed MVP curriculum records for C and data structures.

The catalog below is deliberately explicit: the script only performs the
mechanical YAML expansion so the learning sequence remains reviewable in Git.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "course_packs"


@dataclass(frozen=True)
class Topic:
    code: str
    title: str
    summary: str
    prerequisite: str | None
    source: str
    difficulty: str = "beginner"


C_TOPICS = (
    Topic(
        "BASE-01", "C 程序结构与编译运行", "理解源文件、编译、链接和执行的基本流程。", None, "BASE"
    ),
    Topic(
        "BASE-02",
        "基本类型与取值范围",
        "区分整数、浮点和字符类型，并根据问题选择类型。",
        "BASE-01",
        "BASE",
    ),
    Topic(
        "BASE-03",
        "变量、常量与初始化",
        "正确声明、初始化和更新变量，避免读取未初始化对象。",
        "BASE-02",
        "BASE",
    ),
    Topic(
        "BASE-04",
        "格式化输入输出",
        "使用 printf 与 scanf 的格式说明符完成可靠交互。",
        "BASE-03",
        "BASE",
    ),
    Topic(
        "BASE-05", "算术、关系与逻辑运算", "理解常用运算符、优先级和短路求值。", "BASE-03", "BASE"
    ),
    Topic(
        "BASE-06",
        "类型转换与表达式求值",
        "识别整数除法、提升规则和显式转换的影响。",
        "BASE-05",
        "BASE",
    ),
    Topic(
        "CTRL-01", "if 条件分支", "把互斥业务规则表达为边界清晰的条件分支。", "BASE-05", "CONTROL"
    ),
    Topic(
        "CTRL-02", "switch 多分支", "使用 switch 处理离散选项并避免意外贯穿。", "CTRL-01", "CONTROL"
    ),
    Topic("CTRL-03", "while 与 do-while", "根据先判断或后判断语义选择循环。", "CTRL-01", "CONTROL"),
    Topic(
        "CTRL-04",
        "for 循环与计数模式",
        "用初始化、条件和更新表达确定次数的迭代。",
        "CTRL-03",
        "CONTROL",
    ),
    Topic(
        "CTRL-05",
        "break、continue 与循环边界",
        "控制循环提前结束与跳过，并验证边界条件。",
        "CTRL-04",
        "CONTROL",
    ),
    Topic(
        "FUNC-01",
        "函数声明、定义与调用",
        "使用函数原型拆分程序并理解调用关系。",
        "CTRL-04",
        "CONTROL",
    ),
    Topic(
        "FUNC-02",
        "参数传递与返回值",
        "理解 C 的值传递并用返回值表达计算结果。",
        "FUNC-01",
        "CONTROL",
    ),
    Topic(
        "FUNC-03",
        "作用域、生命周期与存储期",
        "区分块作用域、文件作用域和对象存储期。",
        "FUNC-01",
        "CONTROL",
        "intermediate",
    ),
    Topic(
        "FUNC-04",
        "递归与终止条件",
        "设计具有规模递减和明确终止条件的递归函数。",
        "FUNC-02",
        "CONTROL",
        "intermediate",
    ),
    Topic("ARRAY-01", "一维数组", "按连续同类型元素建模并安全控制下标范围。", "CTRL-04", "MEMORY"),
    Topic(
        "ARRAY-02",
        "二维数组",
        "理解行列布局并实现矩阵式遍历。",
        "ARRAY-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "STR-01", "字符数组与 C 字符串", "理解空字符终止约定和缓冲区容量。", "ARRAY-01", "MEMORY"
    ),
    Topic(
        "STR-02",
        "字符串库函数与边界",
        "在明确容量和终止符的前提下使用字符串函数。",
        "STR-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "PTR-01",
        "指针、地址与解引用",
        "理解指针保存地址以及解引用访问对象的含义。",
        "BASE-03",
        "MEMORY",
    ),
    Topic(
        "PTR-02",
        "指针算术与数组关系",
        "在同一数组对象范围内进行合法指针移动。",
        "PTR-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "PTR-03",
        "指针参数与输出参数",
        "通过指针参数修改调用方对象并检查空指针。",
        "FUNC-02",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "PTR-04",
        "函数指针与回调",
        "用兼容签名的函数指针实现可替换策略。",
        "PTR-01",
        "MEMORY",
        "advanced",
    ),
    Topic(
        "TYPE-01",
        "结构体定义与成员访问",
        "使用结构体组合相关字段并通过点运算符访问。",
        "ARRAY-01",
        "MEMORY",
    ),
    Topic(
        "TYPE-02",
        "结构体数组、嵌套与指针",
        "组织记录集合并正确使用箭头运算符。",
        "TYPE-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "TYPE-03",
        "枚举与联合",
        "使用枚举表达有限状态，理解联合共享存储。",
        "TYPE-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "TYPE-04",
        "typedef 与接口可读性",
        "为复杂类型提供稳定、清晰的接口名称。",
        "TYPE-01",
        "MEMORY",
    ),
    Topic(
        "MEM-01",
        "动态内存分配",
        "使用 malloc/calloc 获取堆内存并检查失败。",
        "PTR-01",
        "MEMORY",
        "intermediate",
    ),
    Topic(
        "MEM-02",
        "realloc、free 与所有权",
        "维护内存所有权，避免泄漏、重复释放和悬空指针。",
        "MEM-01",
        "MEMORY",
        "advanced",
    ),
    Topic(
        "MEM-03",
        "越界、未定义行为与内存诊断",
        "识别越界和失效对象访问，借助工具定位问题。",
        "MEM-02",
        "MEMORY",
        "advanced",
    ),
    Topic(
        "IO-01",
        "文本文件读写",
        "检查打开结果并用循环可靠处理文本记录。",
        "STR-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "IO-02",
        "二进制文件与序列化边界",
        "理解二进制布局的可移植性限制并检查读写数量。",
        "IO-01",
        "ENGINEERING",
        "advanced",
    ),
    Topic(
        "PP-01",
        "预处理、宏与条件编译",
        "安全使用头文件包含、对象宏和条件编译。",
        "FUNC-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "MOD-01",
        "头文件与模块化编程",
        "分离声明和实现，使用包含保护组织多文件程序。",
        "PP-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "MAIN-01",
        "命令行参数",
        "校验 argc 后解析 argv，并向调用者返回状态码。",
        "STR-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "BIT-01",
        "位运算与掩码",
        "使用移位和按位运算表达标志位并避免混淆逻辑运算。",
        "BASE-05",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "QUAL-01",
        "const 与接口约束",
        "用 const 表达只读意图并理解指针限定位置。",
        "PTR-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "ERR-01",
        "错误处理与断言",
        "区分可恢复错误和程序不变量，传播明确错误状态。",
        "FUNC-02",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "DEBUG-01",
        "编译警告、调试与缺陷定位",
        "从警告、最小复现和运行状态系统定位缺陷。",
        "ERR-01",
        "ENGINEERING",
        "intermediate",
    ),
    Topic(
        "TEST-01",
        "边界测试与可验证程序设计",
        "围绕正常、边界和异常输入构造可重复测试。",
        "DEBUG-01",
        "ENGINEERING",
        "advanced",
    ),
)


DS_TOPICS = (
    Topic("FOUND-01", "抽象数据类型与实现", "区分接口语义、数据表示和具体实现。", None, "FOUND"),
    Topic(
        "FOUND-02",
        "算法成本与输入规模",
        "选择基本操作并建立关于输入规模的成本模型。",
        "FOUND-01",
        "FOUND",
    ),
    Topic("FOUND-03", "渐进记号与增长率", "使用 O、Ω、Θ 比较算法增长趋势。", "FOUND-02", "FOUND"),
    Topic(
        "FOUND-04",
        "递归、递推式与调用栈",
        "用规模递减证明终止并分析递归开销。",
        "FOUND-03",
        "FOUND",
        "intermediate",
    ),
    Topic(
        "LINEAR-01",
        "顺序表与随机访问",
        "理解连续存储、索引访问和中间插入成本。",
        "FOUND-01",
        "LINEAR",
    ),
    Topic(
        "LINEAR-02",
        "动态数组与容量扩展",
        "区分长度和容量并理解摊还扩容成本。",
        "LINEAR-01",
        "LINEAR",
        "intermediate",
    ),
    Topic("LINEAR-03", "单链表", "通过结点链接实现线性序列并维护头指针。", "FOUND-01", "LINEAR"),
    Topic(
        "LINEAR-04",
        "双向链表与哨兵",
        "用前后链接和哨兵简化边界操作。",
        "LINEAR-03",
        "LINEAR",
        "intermediate",
    ),
    Topic(
        "LINEAR-05",
        "线性表查找、插入与删除",
        "比较顺序表和链表操作的适用条件与复杂度。",
        "LINEAR-04",
        "LINEAR",
        "intermediate",
    ),
    Topic("STACK-01", "栈及其不变量", "实现后进先出操作并维护栈顶边界。", "LINEAR-01", "LINEAR"),
    Topic(
        "STACK-02",
        "栈的表达式与括号应用",
        "使用栈处理嵌套结构和表达式求值。",
        "STACK-01",
        "LINEAR",
        "intermediate",
    ),
    Topic("QUEUE-01", "队列及其不变量", "实现先进先出操作并维护队首队尾。", "LINEAR-01", "LINEAR"),
    Topic(
        "QUEUE-02",
        "循环队列",
        "通过模运算复用数组空间并区分空与满。",
        "QUEUE-01",
        "LINEAR",
        "intermediate",
    ),
    Topic(
        "QUEUE-03",
        "双端队列",
        "在两端进行受控插入删除并识别典型应用。",
        "QUEUE-02",
        "LINEAR",
        "intermediate",
    ),
    Topic(
        "SORT-01",
        "排序问题、稳定性与下界",
        "明确排序键、稳定性、原地性和比较模型。",
        "FOUND-03",
        "SORTSEARCH",
    ),
    Topic("SORT-02", "插入排序", "维护已排序前缀并分析近乎有序输入。", "SORT-01", "SORTSEARCH"),
    Topic(
        "SORT-03",
        "选择排序与冒泡排序",
        "比较简单二次排序的交换行为和稳定性。",
        "SORT-01",
        "SORTSEARCH",
    ),
    Topic(
        "SORT-04",
        "归并排序",
        "使用分治和线性归并获得稳定的 O(n log n) 排序。",
        "FOUND-04",
        "SORTSEARCH",
        "intermediate",
    ),
    Topic(
        "SORT-05",
        "快速排序",
        "围绕枢轴划分子问题并控制退化风险。",
        "FOUND-04",
        "SORTSEARCH",
        "intermediate",
    ),
    Topic(
        "SORT-06",
        "堆排序",
        "利用堆的选择性质实现原地 O(n log n) 排序。",
        "HEAP-01",
        "SORTSEARCH",
        "advanced",
    ),
    Topic("SEARCH-01", "顺序查找", "在无序序列中线性扫描并处理未命中。", "LINEAR-01", "SORTSEARCH"),
    Topic(
        "SEARCH-02",
        "二分查找与边界",
        "在有序序列上维护不变量并避免区间错误。",
        "SEARCH-01",
        "SORTSEARCH",
        "intermediate",
    ),
    Topic(
        "HASH-01",
        "散列表与散列函数",
        "把键映射到桶并理解装载因子的影响。",
        "FOUND-03",
        "SORTSEARCH",
        "intermediate",
    ),
    Topic(
        "HASH-02",
        "冲突处理与扩容",
        "比较链地址和开放寻址并设计扩容策略。",
        "HASH-01",
        "SORTSEARCH",
        "advanced",
    ),
    Topic(
        "MAP-01",
        "集合与映射抽象",
        "依据成员查询或键值关联选择集合接口。",
        "HASH-01",
        "SORTSEARCH",
        "intermediate",
    ),
    Topic(
        "TREE-01",
        "树、结点关系与基本术语",
        "描述根、父子、深度、高度和子树。",
        "FOUND-01",
        "TREEGRAPH",
    ),
    Topic(
        "TREE-02",
        "二叉树遍历",
        "实现前序、中序、后序和层序遍历。",
        "TREE-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "TREE-03",
        "二叉搜索树",
        "维护左小右大的查找不变量并处理删除情形。",
        "TREE-02",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "TREE-04",
        "平衡搜索树原理",
        "理解旋转如何限制树高并保持搜索次序。",
        "TREE-03",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "HEAP-01",
        "二叉堆",
        "用完全二叉树数组表示维护堆序。",
        "TREE-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "HEAP-02",
        "优先队列",
        "使用堆实现高效最值访问和动态调度。",
        "HEAP-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "GRAPH-01",
        "图与邻接表示",
        "根据稀疏程度选择邻接表或邻接矩阵。",
        "FOUND-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "GRAPH-02",
        "广度优先搜索",
        "使用队列按层访问并求无权最短路。",
        "GRAPH-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "GRAPH-03",
        "深度优先搜索",
        "使用递归或显式栈探索路径并标记访问状态。",
        "GRAPH-01",
        "TREEGRAPH",
        "intermediate",
    ),
    Topic(
        "GRAPH-04",
        "拓扑排序",
        "在有向无环图中生成满足依赖的线性次序。",
        "GRAPH-03",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "GRAPH-05",
        "Dijkstra 最短路径",
        "在非负权图上通过松弛和优先队列求最短路。",
        "HEAP-02",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "GRAPH-06",
        "最小生成树",
        "理解连通无向图的 Kruskal 与 Prim 贪心选择。",
        "GRAPH-01",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "SET-01",
        "并查集",
        "使用路径压缩和按秩合并维护动态连通性。",
        "TREE-01",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "DESIGN-01",
        "分治、贪心与动态规划辨析",
        "依据子问题结构和选择性质匹配算法范式。",
        "FOUND-04",
        "TREEGRAPH",
        "advanced",
    ),
    Topic(
        "EVAL-01",
        "算法边界测试与性能验证",
        "用正确性样例、边界输入和规模实验验证实现。",
        "DESIGN-01",
        "TREEGRAPH",
        "advanced",
    ),
)


C_CODE_TASKS: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "CTRL-01": (
        "读取一个整数，输出 positive、zero 或 negative。",
        (("8\n", "positive\n"), ("0\n", "zero\n"), ("-3\n", "negative\n")),
    ),
    "CTRL-04": (
        "读取正整数 n，输出 1 到 n 的整数和。",
        (("5\n", "15\n"), ("1\n", "1\n"), ("100\n", "5050\n")),
    ),
    "FUNC-01": (
        "实现函数 max2，并读取两个整数输出较大值。",
        (("2 9\n", "9\n"), ("7 7\n", "7\n"), ("-2 -8\n", "-2\n")),
    ),
    "ARRAY-01": (
        "读取 n 及 n 个整数，输出其中最大值。",
        (("5\n3 8 2 9 1\n", "9\n"), ("1\n-4\n", "-4\n"), ("4\n-8 -2 -9 -3\n", "-2\n")),
    ),
    "STR-01": (
        "读取一行不含空格的字符串，输出其长度（不计终止符）。",
        (("hello\n", "5\n"), ("a\n", "1\n"), ("algorithm\n", "9\n")),
    ),
    "PTR-01": (
        "读取两个整数，通过指针交换后按先后顺序输出。",
        (("2 9\n", "9 2\n"), ("7 7\n", "7 7\n"), ("-1 3\n", "3 -1\n")),
    ),
    "TYPE-01": (
        "读取学生姓名与两门整数成绩，输出姓名和总分。",
        (("Li 80 90\n", "Li 170\n"), ("Wu 0 100\n", "Wu 100\n"), ("A 60 60\n", "A 120\n")),
    ),
    "MEM-01": (
        "动态申请 n 个整数，读取后输出平均值，保留两位小数。",
        (("3\n1 2 3\n", "2.00\n"), ("2\n-1 1\n", "0.00\n"), ("1\n5\n", "5.00\n")),
    ),
    "IO-01": (
        "读取若干整数（首项为数量 n），输出可写入文本记录的最小值和最大值。",
        (("4\n3 9 1 5\n", "1 9\n"), ("1\n8\n", "8 8\n"), ("3\n-5 -2 -9\n", "-9 -2\n")),
    ),
    "DEBUG-01": (
        "修复程序：读取 n 个整数并输出其和；不得访问数组边界之外。",
        (("3\n1 2 3\n", "6\n"), ("1\n9\n", "9\n"), ("5\n-2 -1 0 1 2\n", "0\n")),
    ),
}


DS_CODE_TASKS: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "FOUND-04": (
        "读取非负整数 n，使用递归或等价递推输出 n!。",
        (("5\n", "120\n"), ("0\n", "1\n"), ("8\n", "40320\n")),
    ),
    "LINEAR-01": (
        "读取 n 个整数和目标值，输出目标首次出现的下标，不存在输出 -1。",
        (("5\n2 4 4 8 9\n4\n", "1\n"), ("3\n1 2 3\n7\n", "-1\n"), ("1\n5\n5\n", "0\n")),
    ),
    "LINEAR-03": (
        "读取序列并输出逆序结果，体现链式头插或等价操作。",
        (("4\n1 2 3 4\n", "4 3 2 1\n"), ("1\n9\n", "9\n"), ("3\n-1 0 2\n", "2 0 -1\n")),
    ),
    "STACK-01": (
        "判断只含 ()[]{} 的字符串括号是否匹配，输出 true 或 false。",
        (("([]){}\n", "true\n"), ("([)]\n", "false\n"), ("((\n", "false\n")),
    ),
    "QUEUE-01": (
        "模拟队列：读取操作数，push x 入队，pop 输出并删除队首，空队列输出 EMPTY。",
        (
            ("5\npush 3\npush 8\npop\npop\npop\n", "3\n8\nEMPTY\n"),
            ("2\npop\npush 1\n", "EMPTY\n"),
            ("3\npush -1\npop\npop\n", "-1\nEMPTY\n"),
        ),
    ),
    "SORT-02": (
        "读取整数序列，使用插入排序思想升序输出。",
        (("5\n5 2 4 1 3\n", "1 2 3 4 5\n"), ("1\n7\n", "7\n"), ("4\n2 2 -1 3\n", "-1 2 2 3\n")),
    ),
    "SORT-04": (
        "读取整数序列并用归并排序升序输出。",
        (
            ("6\n9 1 8 2 7 3\n", "1 2 3 7 8 9\n"),
            ("2\n1 0\n", "0 1\n"),
            ("4\n-2 -5 -1 -3\n", "-5 -3 -2 -1\n"),
        ),
    ),
    "SEARCH-02": (
        "在有序数组中输出目标首次出现位置，不存在输出 -1。",
        (("6\n1 2 2 2 5 9\n2\n", "1\n"), ("4\n1 3 5 7\n4\n", "-1\n"), ("1\n8\n8\n", "0\n")),
    ),
    "TREE-03": (
        "按顺序插入整数构造二叉搜索树，输出其中序遍历。",
        (("5\n4 2 5 1 3\n", "1 2 3 4 5\n"), ("1\n7\n", "7\n"), ("4\n3 1 4 2\n", "1 2 3 4\n")),
    ),
    "GRAPH-02": (
        "读取无向图和起点，按邻接点编号升序输出 BFS 访问序列。",
        (
            ("4 3\n0 1\n0 2\n1 3\n0\n", "0 1 2 3\n"),
            ("3 2\n0 1\n1 2\n1\n", "1 0 2\n"),
            ("1 0\n0\n", "0\n"),
        ),
    ),
    "GRAPH-05": (
        "读取非负权有向图和起点，输出到各点最短距离，不可达为 INF。",
        (
            ("3 3\n0 1 2\n1 2 3\n0 2 10\n0\n", "0 2 5\n"),
            ("3 1\n0 1 4\n0\n", "0 4 INF\n"),
            ("1 0\n0\n", "0\n"),
        ),
    ),
}


SOURCE_TEXT = {
    (
        "c",
        "BASE",
    ): (
        "C 程序从源文件开始，经预处理、编译和链接形成可执行程序。"
        "类型决定对象的表示和可进行的操作；变量应在首次读取前初始化。"
        "格式化输入输出必须让格式说明符与实参类型一致。"
        "表达式设计需同时考虑优先级、转换、整数除法、溢出和短路求值。"
    ),
    (
        "c",
        "CONTROL",
    ): (
        "分支应覆盖互斥条件和边界值。循环设计要明确初始化、不变量、终止条件和更新。"
        "函数通过清晰的参数、返回值与职责边界降低复杂度；C 默认按值传递。"
        "递归必须具有可到达的终止条件，并让每次调用缩小问题规模。"
    ),
    (
        "c",
        "MEMORY",
    ): (
        "数组元素连续存储，任何下标或指针移动都必须留在合法对象范围。"
        "C 字符串以空字符终止，容量必须包含终止符。"
        "指针的有效性取决于所指对象的生命周期。"
        "动态内存需要明确所有权、失败检查和唯一释放点；"
        "越界、释放后使用与读取未初始化值可能导致未定义行为。"
    ),
    (
        "c",
        "ENGINEERING",
    ): (
        "可靠 C 程序要检查文件、内存和输入操作的结果，"
        "用头文件分离公开声明与实现，并开启编译器警告。"
        "错误状态应能够沿调用链传播。调试从可复现输入、最小失败样例和观测状态开始；"
        "测试需覆盖正常路径、边界、空输入及错误输入。"
    ),
    (
        "data_structures",
        "FOUND",
    ): (
        "抽象数据类型描述可观察操作，实现决定数据如何组织。"
        "算法分析先定义输入规模和基本操作，再用渐进记号描述规模增长趋势。"
        "递归算法必须证明终止，并可通过递推式分析时间与空间成本。"
    ),
    (
        "data_structures",
        "LINEAR",
    ): (
        "顺序表支持常数时间随机访问，但中间插入常需移动元素；"
        "链表通过链接换取局部插入灵活性。栈保持后进先出，队列保持先进先出。"
        "每种结构都应明确空、满、头尾和结点连接等不变量，并在操作后继续保持。"
    ),
    (
        "data_structures",
        "SORTSEARCH",
    ): (
        "排序算法需要同时评价正确性、时间、额外空间、稳定性和输入特征。"
        "二分查找只适用于有序区间，关键是维持搜索区间不变量。"
        "散列表平均性能取决于散列分布、装载因子和冲突处理，最坏情况仍需明确。"
    ),
    (
        "data_structures",
        "TREEGRAPH",
    ): (
        "树以层次关系组织结点，搜索树和堆维护不同不变量。"
        "图可用邻接表或矩阵表示；BFS 使用队列按层扩展，DFS 沿路径深入。"
        "最短路、生成树和拓扑排序各自依赖特定输入条件，"
        "不能只记模板而忽略前提与复杂度。"
    ),
}


def dump(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def runtime(language: str) -> dict[str, Any]:
    return {
        "language": language,
        "version": "C17" if language == "c" else "3.11",
        "entrypoint": "main.c" if language == "c" else "main.py",
        "time_limit_ms": 2000,
        "memory_limit_mb": 128,
        "output_limit_kb": 64,
        "network_access": False,
        "filesystem_access": "isolated",
    }


def source_id(course: str, group: str) -> str:
    prefix = "C" if course == "c" else "DS"
    return f"SRC-{prefix}-GUIDE-{group}"


def build_source(course: str, group: str) -> dict[str, Any]:
    title_course = "C 语言" if course == "c" else "数据结构与算法"
    return {
        "id": source_id(course, group),
        "title": f"{title_course} MVP 教学提要：{group}",
        "course": course,
        "schema_version": "0.1.0",
        "version": 1,
        "source_type": "synthetic",
        "citation": {"locator": f"词元研究所项目组自编 {title_course} {group} 教学提要"},
        "rights": {"basis": "synthetic", "note": "项目组原创教学摘要，可用于课程展示与检索。"},
        "data_classification": "synthetic",
        "rag": {
            "eligible": True,
            "content": {"mode": "inline", "text": SOURCE_TEXT[(course, group)]},
        },
        "status": "reviewed",
    }


def build_objective(exercise_id: str, topic: Topic, course: str, concept_id: str) -> dict[str, Any]:
    return {
        "id": exercise_id,
        "title": f"检查理解：{topic.title}",
        "course": course,
        "schema_version": "0.1.0",
        "version": 1,
        "type": "objective",
        "difficulty": topic.difficulty,
        "estimated_minutes": 5,
        "concept_ids": [concept_id],
        "prompt": f"关于“{topic.title}”，下列哪项最符合本节应掌握的原则？",
        "source_refs": [source_id(course, topic.source)],
        "evaluation": {
            "mode": "exact",
            "options": [
                {"id": "A", "text": topic.summary},
                {"id": "B", "text": "只需记住语法形式，不必验证边界或前置条件。"},
                {"id": "C", "text": "任何实现方式的时间、空间和错误行为都完全相同。"},
                {"id": "D", "text": "模型生成的结论可以替代编译、运行和确定性测试。"},
            ],
            "accepted_answers": ["A"],
        },
        "status": "draft",
    }


def build_code_exercise(
    exercise_id: str,
    topic: Topic,
    course: str,
    concept_id: str,
    language: str,
    task: tuple[str, tuple[tuple[str, str], ...]],
) -> dict[str, Any]:
    prompt, cases = task
    tests = [
        {
            "id": f"case-{index + 1}",
            "visibility": "public" if index == 0 else "hidden",
            "input": input_text,
            "expected_output": expected,
        }
        for index, (input_text, expected) in enumerate(cases)
    ]
    exercise_type = "debug" if topic.code == "DEBUG-01" else "code"
    evaluation: dict[str, Any] = {"mode": "tests", "runtime": runtime(language), "tests": tests}
    if exercise_type == "debug":
        evaluation["starter_code"] = (
            "#include <stdio.h>\nint main(void){int n,a[100],sum=0; "
            'scanf("%d",&n); for(int i=0;i<=n;i++){scanf("%d",&a[i]);sum+=a[i];} '
            'printf("%d\\n",sum);return 0;}'
        )
    return {
        "id": exercise_id,
        "title": f"编程实践：{topic.title}",
        "course": course,
        "schema_version": "0.1.0",
        "version": 1,
        "type": exercise_type,
        "difficulty": topic.difficulty,
        "estimated_minutes": 20,
        "concept_ids": [concept_id],
        "prompt": prompt,
        "source_refs": [source_id(course, topic.source)],
        "evaluation": evaluation,
        "status": "draft",
    }


def build_pack(course: str, title: str, owner: str, topics: tuple[Topic, ...]) -> None:
    pack = PACKS / course
    prefix = "C" if course == "c" else "DS"
    code_tasks = C_CODE_TASKS if course == "c" else DS_CODE_TASKS
    language = "c" if course == "c" else "python"

    groups = list(dict.fromkeys(topic.source for topic in topics))
    for group in groups:
        record = build_source(course, group)
        dump(pack / "sources" / f"{record['id']}.yaml", record)

    for topic in topics:
        concept_id = f"{prefix}-{topic.code}"
        exercise_suffix = "C1" if topic.code in code_tasks else "Q1"
        exercise_id = f"{concept_id}-{exercise_suffix}"
        record = {
            "id": concept_id,
            "title": topic.title,
            "course": course,
            "schema_version": "0.1.0",
            "version": 1,
            "difficulty": topic.difficulty,
            "estimated_minutes": 30,
            "prerequisites": [f"{prefix}-{topic.prerequisite}"] if topic.prerequisite else [],
            "learning_objectives": [
                f"能够解释{topic.title}的核心规则",
                f"能够运用{topic.title}解决边界明确的问题",
            ],
            "concepts": [topic.title, "边界条件", "可验证性"],
            "lesson": {
                "summary": topic.summary,
                "key_points": [topic.summary, "先说明适用前提，再通过示例或测试验证结论。"],
                "common_mistakes": ["忽略输入边界或算法前置条件", "只观察单个样例就判断实现正确"],
            },
            "assessment_ids": [exercise_id],
            "source_refs": [source_id(course, topic.source)],
            "status": "draft",
        }
        dump(pack / "concepts" / f"{concept_id}.yaml", record)
        exercise = (
            build_code_exercise(
                exercise_id, topic, course, concept_id, language, code_tasks[topic.code]
            )
            if topic.code in code_tasks
            else build_objective(exercise_id, topic, course, concept_id)
        )
        dump(pack / "exercises" / f"{exercise_id}.yaml", exercise)

    manifest = {
        "schema_version": "0.1.0",
        "course": {
            "id": course,
            "title": title,
            "status": "draft",
            "target_core_concepts": 40,
            "implemented_core_concepts": len(topics),
        },
        "content": {
            "concepts_dir": "concepts",
            "exercises_dir": "exercises",
            "projects_dir": "projects",
            "sources_dir": "sources",
        },
        "features": {
            "rag_qa": "in_progress",
            "adaptive_practice": "in_progress",
            "debug_tasks": "in_progress",
            "comprehensive_project": "in_progress",
        },
        "review": {"content_owner": owner, "last_reviewed_at": None},
    }
    dump(pack / "manifest.yaml", manifest)


def build_projects() -> None:
    c_project = {
        "id": "C-PROJ-RECORD-01",
        "title": "命令行记录管理器",
        "course": "c",
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "intermediate",
        "estimated_minutes": 180,
        "concept_ids": ["C-TYPE-01", "C-PTR-03", "C-MEM-01", "C-IO-01", "C-DEBUG-01", "C-TEST-01"],
        "summary": "使用 C17 实现可从文本文件读取、查询、排序并保存记录的命令行程序。",
        "requirements": [
            "使用结构体表达记录",
            "动态管理记录集合",
            "检查输入、内存和文件错误",
            "覆盖空文件、单条记录和重复键",
        ],
        "deliverables": ["可编译的多文件 C 源码", "构建与运行说明", "边界测试清单"],
        "source_refs": ["SRC-C-GUIDE-MEMORY", "SRC-C-GUIDE-ENGINEERING"],
        "verification_exercise_ids": ["C-IO-01-C1", "C-DEBUG-01-C1"],
        "scenario_scope": "none",
        "scenario_provider": "none",
        "data_classification": "synthetic",
        "computer_science_objectives": [
            "综合运用结构体、指针、动态内存和文件处理",
            "通过确定性测试验证边界与错误路径",
        ],
        "business_context_objectives": [],
        "evaluation": {
            "mode": "rubric",
            "max_score": 100,
            "rubric": [
                {"criterion": "功能与确定性测试", "points": 55},
                {"criterion": "内存和错误处理", "points": 25},
                {"criterion": "模块化与说明", "points": 20},
            ],
        },
        "status": "draft",
    }
    ds_project = {
        "id": "DS-PROJ-NETWORK-01",
        "title": "合成供应链网络路径分析",
        "course": "data_structures",
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "advanced",
        "estimated_minutes": 240,
        "concept_ids": ["DS-GRAPH-01", "DS-GRAPH-02", "DS-GRAPH-05", "DS-HEAP-02", "DS-EVAL-01"],
        "summary": "在固定合成的供应链网络上实现可达性与非负权最短路径分析，技术评价聚焦图算法。",
        "requirements": [
            "解析顶点和带权边数据",
            "实现 BFS 与 Dijkstra",
            "处理孤立点、不可达点和重复边",
            "报告复杂度与测试证据",
        ],
        "deliverables": ["可运行的 Python 3.11 程序", "算法与复杂度说明", "边界测试和结果解释"],
        "source_refs": ["SRC-DS-GUIDE-TREEGRAPH"],
        "verification_exercise_ids": ["DS-GRAPH-02-C1", "DS-GRAPH-05-C1"],
        "scenario_scope": "post_course_finance_practice",
        "scenario_provider": "fixed_synthetic",
        "data_classification": "synthetic",
        "computer_science_objectives": [
            "选择图表示并实现图遍历与最短路径",
            "用边界测试验证算法前置条件和输出",
        ],
        "business_context_objectives": [
            "把合成业务字段转换为图模型",
            "说明算法结果的适用前提，不作真实经营决策",
        ],
        "evaluation": {
            "mode": "rubric",
            "max_score": 100,
            "rubric": [
                {"criterion": "算法正确性与测试", "points": 60},
                {"criterion": "复杂度与边界分析", "points": 25},
                {"criterion": "结果解释", "points": 15},
            ],
        },
        "status": "draft",
    }
    dump(PACKS / "c" / "projects" / f"{c_project['id']}.yaml", c_project)
    dump(PACKS / "data_structures" / "projects" / f"{ds_project['id']}.yaml", ds_project)


def build_python_support() -> None:
    """Add RAG-ready original guides and the Python capstone without replacing owned lessons."""

    guides = {
        "BASE": (
            "Python 程序由语句和表达式组成，变量名绑定对象。条件与循环应覆盖边界，"
            "容器选择取决于是否需要顺序、唯一性或键值关联。函数通过参数、返回值和职责边界"
            "组织逻辑；代码生成结论必须通过实际运行和测试确认。"
        ),
        "FUNCTIONS": (
            "函数设计应让输入、输出和副作用清晰。默认参数在定义时求值，作用域遵循局部、"
            "闭包、全局和内置名称查找。迭代器按需产生元素，生成器用暂停与恢复表达数据流，"
            "适合避免一次性加载全部数据。"
        ),
        "DATA": (
            "数据处理先确认字段、类型和缺失约定，再执行解析、校验、转换、聚合与输出。"
            "异常不能被静默吞掉；每条清洗规则应有正常、边界和错误样例。财经背景只提供"
            "字段语义和约束，课程评价仍以程序结构、数据处理和测试证据为核心。"
        ),
        "ENGINEERING": (
            "可维护 Python 项目应拆分模块、隔离文件与网络副作用、记录错误上下文，并使用"
            "自动化测试验证公开行为。调试应先固定失败输入，再缩小复现范围，比较期望与实际，"
            "最后增加回归测试防止同类缺陷再次出现。"
        ),
        "CASE-FALLBACK": (
            "固定合成数据集包含月份、品类、收入、成本和状态字段；缺失收入、负成本和重复记录"
            "被人为注入，用于练习解析、校验、清洗、聚合与异常报告。所有主体与数值均为虚构，"
            "不得用于真实经营判断。"
        ),
    }
    for group, text in guides.items():
        record_id = f"SRC-PY-GUIDE-{group}"
        record = {
            "id": record_id,
            "title": f"Python MVP 教学提要：{group}",
            "course": "python",
            "schema_version": "0.1.0",
            "version": 1,
            "source_type": "synthetic",
            "citation": {"locator": f"词元研究所项目组自编 Python {group} 教学提要"},
            "rights": {"basis": "synthetic", "note": "项目组原创教学摘要，可用于课程展示与检索。"},
            "data_classification": "synthetic",
            "rag": {"eligible": True, "content": {"mode": "inline", "text": text}},
            "status": "reviewed",
        }
        dump(PACKS / "python" / "sources" / f"{record_id}.yaml", record)

    project = {
        "id": "PY-PROJ-FINANCE-DATA-01",
        "title": "脱敏经营数据质量分析",
        "course": "python",
        "schema_version": "0.1.0",
        "version": 1,
        "difficulty": "intermediate",
        "estimated_minutes": 240,
        "concept_ids": [
            "PY-FUNC-01",
            "PY-DICT-01",
            "PY-EXC-01",
            "PY-FILE-03",
            "PY-DATA-01",
        ],
        "summary": ("读取脱敏或固定合成的经营记录，完成字段校验、异常分类、统计汇总和可追溯报告。"),
        "requirements": [
            "把解析、校验、清洗和汇总拆分为可测试函数",
            "处理缺失值、非法数值和重复记录",
            "保留原始行号与错误原因，不静默删除异常",
            "驼灵不可用时自动使用固定合成背景完成同一编程任务",
        ],
        "deliverables": ["可运行的 Python 3.11 程序", "自动化测试", "数据质量报告与限制说明"],
        "source_refs": ["SRC-PY-GUIDE-DATA", "SRC-PY-GUIDE-ENGINEERING"],
        "verification_exercise_ids": ["PY-DATA-01-C1", "PY-FILE-03-C1"],
        "scenario_scope": "post_course_finance_practice",
        "scenario_provider": "tuoling",
        "data_classification": "authorized_desensitized",
        "computer_science_objectives": [
            "使用函数、字典、异常和文件处理实现数据管道",
            "用确定性测试验证清洗规则和错误路径",
        ],
        "business_context_objectives": [
            "理解脱敏经营字段的含义与约束",
            "解释数据质量结论的适用范围，不替代真实业务决策",
        ],
        "evaluation": {
            "mode": "rubric",
            "max_score": 100,
            "rubric": [
                {"criterion": "程序正确性与测试", "points": 55},
                {"criterion": "异常处理与可追溯性", "points": 25},
                {"criterion": "模块化与结果解释", "points": 20},
            ],
        },
        "fallback": {
            "mode": "fixed_synthetic",
            "source_refs": ["SRC-PY-GUIDE-CASE-FALLBACK"],
            "note": "驼灵不可用或授权数据缺失时使用固定合成字段和记录继续编程练习。",
        },
        "status": "draft",
    }
    dump(PACKS / "python" / "projects" / f"{project['id']}.yaml", project)

    manifest_path = PACKS / "python" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["features"].update(
        {
            "rag_qa": "in_progress",
            "adaptive_practice": "in_progress",
            "debug_tasks": "in_progress",
            "comprehensive_project": "in_progress",
        }
    )
    dump(manifest_path, manifest)


def main() -> None:
    if len(C_TOPICS) != 40 or len(DS_TOPICS) != 40:
        raise RuntimeError("MVP catalogs must contain exactly 40 topics per course")
    build_pack("c", "C语言程序设计", "王维庸", C_TOPICS)
    build_pack("data_structures", "数据结构与算法", "曾毅杨", DS_TOPICS)
    build_projects()
    build_python_support()
    print("Built C and data-structures MVP course packs.")


if __name__ == "__main__":
    main()
