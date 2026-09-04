"""Enrich the 120 MVP concept cards to the course-content v2 baseline.

This script is deterministic and deliberately keeps all teaching records in
``draft``. It improves review material; it never claims teacher approval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "course_packs"
COURSES = ("c", "python", "data_structures")
TEMPLATE_MISTAKES = {
    "忽略输入边界或算法前置条件",
    "只观察单个样例就判断实现正确",
}


class Detail(NamedTuple):
    key_points: tuple[str, str, str]
    examples: tuple[str, ...]
    mistakes: tuple[str, str]


CORE_DETAILS: dict[str, Detail] = {
    "C-BASE-01": Detail(
        (
            "源文件先经预处理和编译生成目标文件，再由链接器解析外部符号形成可执行程序。",
            "main 是程序入口，成功通常返回 0；声明、语句和表达式必须处于合法的作用域。",
            "开启 -std=c17 -Wall -Wextra，把编译警告视为需要解释和修复的质量信号。",
        ),
        ("命令示例：gcc -std=c17 -Wall -Wextra main.c -o main，然后运行生成的程序。",),
        (
            "把编译和链接混为一谈，找不到函数定义时仍只检查语法。",
            "忽略警告，导致类型不匹配或未声明函数进入运行阶段。",
        ),
    ),
    "C-BASE-04": Detail(
        (
            "printf 的格式说明符必须匹配实参提升后的类型，scanf 还必须传入可写对象的地址。",
            "检查 scanf 的返回值，只有成功转换的字段数符合预期时才能使用读入结果。",
            "为字符串输入设置最大宽度，并把换行、空白和缓冲区容量纳入接口设计。",
        ),
        ('代码示例：int n; if (scanf("%d", &n) != 1) return 1; printf("%d\\n", n);',),
        (
            "scanf 读取整数时写成 n 而不是 &n，造成无效写入。",
            "用 %d 输出 long 或 size_t，产生类型不匹配和未定义行为。",
        ),
    ),
    "C-CTRL-01": Detail(
        (
            "条件表达式的结果为零或非零，分支顺序会影响重叠条件最终落入哪一条路径。",
            "互斥区间应从边界值开始设计，例如负数、零和正数必须完整且不重叠。",
            "复杂条件先命名中间布尔含义，并利用短路求值保护除法或指针解引用。",
        ),
        (
            '代码示例：if (x > 0) puts("positive"); '
            'else if (x == 0) puts("zero"); else puts("negative");',
        ),
        (
            "把比较写成赋值，例如 if (x = 0)，导致条件和变量同时被改变。",
            "只测试典型正数，没有覆盖等号对应的边界值。",
        ),
    ),
    "C-CTRL-04": Detail(
        (
            "for 的初始化只执行一次，条件在每轮前判断，更新表达式在循环体后执行。",
            "计数循环应明确闭区间或半开区间，数组遍历通常使用 0 <= i < n。",
            "循环不变量描述每轮开始时已经完成的工作，可用于检查算法和边界是否正确。",
        ),
        ("代码示例：long long sum = 0; for (int i = 1; i <= n; ++i) sum += i;",),
        (
            "把 i < n 写成 i <= n 后访问 a[n]，发生越界。",
            "更新方向与终止条件相反，循环永远无法结束。",
        ),
    ),
    "C-FUNC-01": Detail(
        (
            "函数原型让编译器在调用点检查参数数量、参数类型和返回类型。",
            "函数定义包含唯一实现，调用表达式建立新的调用帧并在返回后继续执行。",
            "一个函数应有单一、可测试的职责，并通过参数和返回值显式表达接口。",
        ),
        ("代码示例：int max2(int a, int b); int max2(int a, int b) { return a > b ? a : b; }",),
        (
            "调用前没有可见原型，导致编译器无法进行完整类型检查。",
            "声明和定义的参数或返回类型不一致，造成冲突接口。",
        ),
    ),
    "C-ARRAY-01": Detail(
        (
            "数组在创建时确定元素类型和长度，合法下标范围始终是 0 到 n-1。",
            "数组作为函数实参时通常退化为首元素指针，因此长度必须通过独立参数传递。",
            "初始化、遍历和聚合都要先处理空序列约定，再维护当前已处理区间的不变量。",
        ),
        ("代码示例：int max = a[0]; for (size_t i = 1; i < n; ++i) if (a[i] > max) max = a[i];",),
        (
            "使用 sizeof(形参数组) 推断调用方数组长度，实际得到的是指针大小。",
            "循环访问 a[n] 或在 n 为 0 时直接读取 a[0]。",
        ),
    ),
    "C-PTR-01": Detail(
        (
            "取地址运算符 & 获得对象地址，指针变量保存兼容类型的地址，*p 访问所指对象。",
            "解引用前必须证明指针非空、指向仍处于生命周期内且满足对齐与类型要求。",
            "修改调用方对象时传入其地址，同时用清晰命名和 const 标注读写意图。",
        ),
        ("代码示例：void swap(int *a, int *b) { int t = *a; *a = *b; *b = t; }",),
        (
            "未初始化指针就执行 *p = 1，向不确定地址写入。",
            "返回局部变量地址，函数结束后指针立即悬空。",
        ),
    ),
    "C-STR-01": Detail(
        (
            "C 字符串是以 '\\0' 结尾的字符序列，缓冲区容量必须包含终止符位置。",
            "字符串长度不包含终止符，但复制和拼接时必须为终止符保留空间。",
            "读取和遍历必须设置上界，不能假设外部输入一定包含合法终止符。",
        ),
        ('代码示例：char name[16]; if (scanf("%15s", name) == 1) printf("%zu\\n", strlen(name));',),
        (
            "为5个可见字符只分配 char s[5]，没有终止符空间。",
            "用 == 比较两个字符数组内容，而不是使用受控的字符串比较。",
        ),
    ),
    "C-TYPE-01": Detail(
        (
            "结构体把不同类型但属于同一实体的字段组合为一个对象。",
            "普通对象使用点运算符访问成员，结构体指针使用箭头运算符访问成员。",
            "初始化时明确每个字段含义，跨文件共享结构体声明时放入受保护的头文件。",
        ),
        (
            "代码示例：struct Student { char name[16]; int score; }; "
            'struct Student s = {.name = "Li", .score = 90};',
        ),
        (
            "复制字符串字段时忽略数组容量，覆盖相邻成员。",
            "改变结构体字段后仍按旧的二进制布局读写文件。",
        ),
    ),
    "C-MEM-01": Detail(
        (
            "malloc 返回未初始化的动态存储，calloc 会把分配字节置零，但都可能失败。",
            "分配大小应以元素数量乘 sizeof *ptr 计算，并在乘法前防止整数溢出。",
            "每块成功分配的内存必须有明确所有者和唯一释放路径，失败分支同样要清理。",
        ),
        ("代码示例：int *a = malloc(n * sizeof *a); if (a == NULL) return 1; /* use */ free(a);",),
        (
            "写成 malloc(n) 却按 n 个 int 使用，导致分配空间不足。",
            "未检查返回值便解引用，内存不足时触发崩溃。",
        ),
    ),
    "C-DEBUG-01": Detail(
        (
            "先固定失败输入和期望结果，再把问题缩减为稳定可复现的最小程序。",
            "编译警告、断点、调用栈和变量观察共同构成证据，不能凭猜测连续改代码。",
            "修复后增加回归测试，并重新运行正常、边界和失败路径。",
        ),
        ("调试示例：对数组求和错误先用 n=1 复现，再观察循环最后一次的 i 是否等于 n。",),
        ("一次修改多个位置，测试通过后无法判断真正原因。", "只消除崩溃而不验证结果值和越界行为。"),
    ),
    "C-TEST-01": Detail(
        (
            "测试从接口契约推导正常、边界、无效和资源受限输入，而不是从实现细节凑样例。",
            "每个用例必须有确定输入、预期输出和失败诊断，隐藏测试不能泄露给模型或前端。",
            "回归测试记录曾经失败的最小样例，代码修改后自动验证缺陷没有重新出现。",
        ),
        ("示例：最大值函数至少覆盖单元素、全负数、重复最大值和空输入处理约定。",),
        (
            "只测试一个正常样例就宣称程序正确。",
            "让语言模型决定通过与否，而不是使用编译和确定性断言。",
        ),
    ),
    "PY-BASE-02": Detail(
        (
            "Python 名称绑定对象，赋值不会声明固定类型；对象类型决定可执行的操作。",
            "int、float、str、bool 的转换需要明确输入约定，失败时应处理 ValueError。",
            "使用 type 和 isinstance 观察类型，但程序接口更应通过行为和测试表达约束。",
        ),
        ("代码示例：age_text = '20'; age = int(age_text); is_adult = age >= 18",),
        (
            "把 input 返回值当作整数直接相加。",
            "用变量名 str、list 覆盖内置类型，导致后续调用失败。",
        ),
    ),
    "PY-BASE-04": Detail(
        (
            "input 每次返回去掉行尾的字符串，数值计算前必须完成显式转换。",
            "print 可通过 sep、end 和格式化字符串控制输出，评测输出必须严格匹配约定。",
            "解析失败应给出清晰错误或受控退出，不能让未校验数据进入后续计算。",
        ),
        ("代码示例：count = int(input().strip()); print(f'count={count}')",),
        (
            "忘记转换输入，得到字符串拼接而不是数值加法。",
            "在评测输出中加入多余提示文字，导致确定性比较失败。",
        ),
    ),
    "PY-BASE-05": Detail(
        (
            "if、elif、else 按顺序选择第一条为真的路径，缩进定义分支代码块。",
            "区间判断可以使用链式比较，边界上的等号必须与题目契约一致。",
            "复杂条件优先拆成有含义的布尔变量，避免重复计算和难以测试的长表达式。",
        ),
        ("代码示例：label = 'positive' if x > 0 else ('zero' if x == 0 else 'negative')",),
        (
            "混用制表符和空格造成缩进错误。",
            "把多个独立 if 当作互斥分支，导致同一输入执行多段逻辑。",
        ),
    ),
    "PY-BASE-07": Detail(
        (
            "for 直接遍历可迭代对象；range(start, stop, step) 不包含 stop。",
            "需要索引时使用 enumerate，需要并行遍历时使用 zip，而不是手工维护多个下标。",
            "循环前明确空输入、步长方向和聚合初值，循环后验证边界结果。",
        ),
        ("代码示例：total = sum(value for value in range(1, n + 1))",),
        ("认为 range(1, n) 会包含 n，产生少一次循环。", "遍历列表时同时删除元素，造成元素被跳过。"),
    ),
    "PY-LIST-01": Detail(
        (
            "列表是有序、可变容器，索引范围为 -len(items) 到 len(items)-1。",
            "切片创建浅拷贝并使用半开区间，嵌套可变对象仍然可能被多个列表共享。",
            "空列表访问、越界和别名修改必须通过接口约定与测试显式处理。",
        ),
        ("代码示例：values = [3, 1, 4]; first, tail = values[0], values[1:]",),
        (
            "用 [[0] * 3] * 3 创建二维列表，导致三行引用同一个内部列表。",
            "在列表为空时直接读取 items[0]。",
        ),
    ),
    "PY-DICT-01": Detail(
        (
            "字典把可散列且相等语义稳定的键映射到值，键在一个字典中唯一。",
            "使用 get、in 或 setdefault 明确缺失键策略，不应无条件索引未知外部键。",
            "遍历 items 可同时获得键和值，插入顺序不等于业务排序规则。",
        ),
        ("代码示例：counts = {}; counts[word] = counts.get(word, 0) + 1",),
        (
            "直接读取 counts[word]，首次出现时触发 KeyError。",
            "使用列表作为字典键，因其可变且不可散列而报错。",
        ),
    ),
    "PY-FUNC-01": Detail(
        (
            "def 创建函数对象并绑定名称，函数体只在调用时执行。",
            "参数接收输入，return 结束当前调用并返回结果；省略 return 时返回 None。",
            "函数应职责单一、输入输出明确，并尽量把文件和网络副作用留在边界层。",
        ),
        ("代码示例：def add(a: int, b: int) -> int: return a + b",),
        (
            "只计算结果却忘记 return，调用方得到 None。",
            "函数依赖未声明的全局可变状态，导致测试互相影响。",
        ),
    ),
    "PY-FUNC-02": Detail(
        (
            "位置参数按顺序绑定，关键字参数按名称绑定，调用必须满足函数签名。",
            "默认值在函数定义时求值，不能把可变对象直接作为会被修改的默认值。",
            "返回多个结果本质上是返回元组，调用方应明确每个位置的语义。",
        ),
        (
            "代码示例：def append_item(item, items=None): "
            "items = [] if items is None else items; items.append(item); return items",
        ),
        (
            "使用 items=[] 作为可变默认值，多个调用共享同一列表。",
            "混淆 print 和 return，导致函数难以复用和测试。",
        ),
    ),
    "PY-EXC-01": Detail(
        (
            "try 只包围可能失败的最小操作，except 捕获能够处理的具体异常类型。",
            "else 用于没有异常时的后续逻辑，finally 用于无论成功失败都必须执行的清理。",
            "异常信息应保留输入位置和操作上下文，但不得泄露密钥或学生敏感数据。",
        ),
        ("代码示例：try: value = int(text)\nexcept ValueError: value = None",),
        (
            "使用 except Exception: pass 静默吞掉所有错误。",
            "把程序缺陷当作正常分支长期依赖异常控制。",
        ),
    ),
    "PY-FILE-02": Detail(
        (
            "with 在代码块退出时调用上下文管理协议，异常发生时也能可靠释放资源。",
            "打开文本文件时显式指定编码和模式，避免平台默认编码造成不可复现结果。",
            "路径、权限和格式错误需要转成面向用户的受控诊断。",
        ),
        ("代码示例：with open(path, 'r', encoding='utf-8') as stream: text = stream.read()",),
        (
            "离开 with 代码块后继续使用已经关闭的文件对象。",
            "省略编码并假设所有机器的默认设置相同。",
        ),
    ),
    "PY-DATA-01": Detail(
        (
            "数据清洗先定义字段、类型、缺失值、重复记录和异常范围，再编写转换规则。",
            "每条规则保留原值、处理结果和失败原因，避免无法追溯的静默修改。",
            "课程中的财经字段只提供脱敏业务语义，评分仍以解析、校验、测试和代码结构为核心。",
        ),
        ("示例：把空字符串收入标为 missing，把负成本记录为 invalid，并输出对应行号。",),
        (
            "直接删除所有异常行而不记录数量和原因。",
            "用业务结论替代对数据类型、缺失和边界的程序验证。",
        ),
    ),
    "PY-ALGO-01": Detail(
        (
            "选择排序或查找方法前先确认输入是否有序、是否需要稳定性以及数据规模。",
            "Python 的 sorted 返回新列表，list.sort 原地修改；key 函数只描述排序键。",
            "二分查找必须维护半开或闭区间不变量，并明确重复元素时返回哪一个位置。",
        ),
        ("代码示例：ordered = sorted(records, key=lambda item: (item['score'], item['id']))",),
        ("调用 list.sort 后把返回值赋给变量，得到 None。", "在未排序数据上直接执行二分查找。"),
    ),
    "DS-FOUND-02": Detail(
        (
            "先选择输入规模 n 和能够代表主要开销的基本操作，再统计其执行次数。",
            "最坏、平均和最好情况回答不同问题，分析时必须声明采用哪一种。",
            "时间和额外空间分别建模，不能用一次小规模计时直接代替增长率分析。",
        ),
        ("示例：顺序查找最坏情况下比较 n 次，因此时间随输入长度线性增长。",),
        ("只统计源代码行数而忽略循环执行次数。", "把某台电脑的一次运行毫秒数直接写成算法复杂度。"),
    ),
    "DS-FOUND-03": Detail(
        (
            "O 给出渐进上界，Ω 给出渐进下界，Θ 表示上下界同阶。",
            "忽略常数和低阶项只适用于足够大的输入规模，不能抹去不同输入模型。",
            "比较增长率时同时说明时间、空间及最坏或平均情形。",
        ),
        ("示例：3n²+5n+7 属于 Θ(n²)，因为高阶项在 n 增大时主导增长。",),
        ("把 O(n²) 当成必须恰好执行 n² 次。", "认为两个 O(n) 算法在所有输入和机器上速度完全相同。"),
    ),
    "DS-LINEAR-01": Detail(
        (
            "顺序表使用连续存储，通过下标常数时间访问元素。",
            "中间插入或删除需要移动后续元素，尾部扩展还可能触发整体重新分配。",
            "长度表示已有元素数量，容量表示可用槽位；合法访问区间始终是 0 到 length-1。",
        ),
        ("示例：长度5的顺序表在下标2插入元素，需要把原下标2到4的元素依次后移。",),
        (
            "把容量当作长度并读取尚未初始化的槽位。",
            "从前向后移动元素完成插入，覆盖还没搬走的数据。",
        ),
    ),
    "DS-LINEAR-03": Detail(
        (
            "单链表结点保存数据和后继引用，头指针确定整个可达序列。",
            "已知前驱时插入和删除只改常数个链接，但按位置查找仍需线性遍历。",
            "操作后必须保持无意外环、尾结点后继为空和所有有效结点可达。",
        ),
        ("示例：在结点 p 后插入 q 时，先令 q.next=p.next，再令 p.next=q。",),
        (
            "先修改 p.next 再保存旧后继，导致后半段链表丢失。",
            "删除结点后仍保留并使用指向该结点的失效引用。",
        ),
    ),
    "DS-STACK-01": Detail(
        (
            "栈只在同一端压入和弹出，保持后进先出顺序。",
            "数组实现维护 top 边界，链式实现维护栈顶结点；空栈弹出必须有明确策略。",
            "调用栈、括号匹配和深度优先过程都依赖尚未完成任务的逆序恢复。",
        ),
        ("示例：扫描 '([])' 时遇到左括号压栈，右括号必须与当前栈顶类型匹配。",),
        ("遇到任意右括号都只弹栈，不检查括号类型。", "空栈时仍读取栈顶元素。"),
    ),
    "DS-QUEUE-02": Detail(
        (
            "循环队列用模运算让队首和队尾在数组末端后回到开头。",
            "必须通过保留空槽、记录元素数或额外标志区分 front==rear 时的空与满。",
            "入队先检查容量，出队先检查空状态，操作后再更新对应索引。",
        ),
        ("示例：容量5且采用保留空槽时，(rear+1)%5==front 表示队列已满。",),
        ("把 front==rear 同时解释为空和满，状态不可判定。", "索引递增后不取模，最终越过数组边界。"),
    ),
    "DS-SORT-04": Detail(
        (
            "归并排序递归地把序列分半，分别排序后在线性时间内合并两个有序段。",
            "合并时相等元素优先取左段可以保持稳定性。",
            "时间复杂度为 Θ(n log n)，典型数组实现需要 Θ(n) 辅助空间。",
        ),
        ("示例：合并 [2,5] 与 [1,4,6] 时依次比较段首，得到 [1,2,4,5,6]。",),
        ("合并结束后忘记复制某一侧剩余元素。", "递归区间没有严格缩小，导致无限递归。"),
    ),
    "DS-SEARCH-02": Detail(
        (
            "二分查找只适用于按同一比较规则有序且支持随机访问的区间。",
            "采用半开区间 [left,right) 时，循环条件为 left<right，每轮必须严格缩小区间。",
            "查找首次出现位置要在相等时继续收缩右边界，而不是立即返回任意命中。",
        ),
        ("示例：在 [1,2,2,2,5] 查找首个2，相等时令 right=mid，最终得到下标1。",),
        ("在无序数组上使用二分查找。", "混用闭区间与半开区间公式，遗漏端点或形成死循环。"),
    ),
    "DS-HASH-01": Detail(
        (
            "散列函数把键稳定映射到桶位置，相等键必须产生相同散列结果。",
            "冲突不可避免，需要链地址或开放寻址等策略保存多个映射。",
            "装载因子影响平均查找长度，达到阈值时通常需要扩容并重新散列。",
        ),
        ("示例：容量8时可先用 hash(key)%8 选桶；不同键落入同一桶时再执行冲突策略。",),
        ("假设散列值不同，因此不实现冲突处理。", "扩容后只复制旧桶位置，没有按新容量重新散列。"),
    ),
    "DS-TREE-02": Detail(
        (
            "前序按根左右、中序按左根右、后序按左右根访问，层序使用队列逐层访问。",
            "递归遍历的空树是直接返回的基本情形，显式栈实现要保存尚未处理的路径。",
            "每个结点恰好访问一次，因此遍历时间为 Θ(n)，递归空间取决于树高。",
        ),
        ("示例：根A、左子B、右子C的前序为 A B C，中序为 B A C，后序为 B C A。",),
        ("把访问根结点的位置写错，导致三种深度遍历结果相同。", "忽略极度倾斜树的递归深度风险。"),
    ),
    "DS-GRAPH-02": Detail(
        (
            "BFS 用队列保存已发现但尚未展开的顶点，按距离层次访问。",
            "顶点入队时立即标记已访问，避免同一顶点被多个邻居重复加入。",
            "在无权图中首次到达顶点的层数就是最少边数距离，并可用前驱数组恢复路径。",
        ),
        ("示例：从0出发，先将0入队；弹出0后把所有未访问邻点标记并依次入队。",),
        (
            "顶点出队时才标记，造成队列中大量重复顶点。",
            "图不连通时只从一个起点运行却宣称遍历了整张图。",
        ),
    ),
    "DS-GRAPH-05": Detail(
        (
            "Dijkstra 适用于边权非负的图，通过松弛不断改进从源点到各点的上界。",
            "优先队列每次选择当前距离最小的未确定顶点，过期队列项应被跳过。",
            "使用前驱数组恢复路径，并单独表示不可达距离，防止无穷值参与溢出运算。",
        ),
        ("示例：若 dist[u]+w(u,v)<dist[v]，则更新 dist[v] 和 predecessor[v] 并重新入队。",),
        (
            "图中存在负权边仍使用 Dijkstra，已确定距离可能被后来路径改小。",
            "只输出距离而不检查顶点是否不可达。",
        ),
    ),
}


PYTHON_SOURCE_BY_PREFIX = {
    "BASE": "SRC-PY-GUIDE-BASE",
    "STR": "SRC-PY-GUIDE-BASE",
    "LIST": "SRC-PY-GUIDE-BASE",
    "TUPLE": "SRC-PY-GUIDE-BASE",
    "DICT": "SRC-PY-GUIDE-BASE",
    "SET": "SRC-PY-GUIDE-BASE",
    "CONTAINER": "SRC-PY-GUIDE-BASE",
    "FUNC": "SRC-PY-GUIDE-FUNCTIONS",
    "ITER": "SRC-PY-GUIDE-FUNCTIONS",
    "ALGO": "SRC-PY-GUIDE-FUNCTIONS",
    "DATA": "SRC-PY-GUIDE-DATA",
    "MOD": "SRC-PY-GUIDE-ENGINEERING",
    "EXC": "SRC-PY-GUIDE-ENGINEERING",
    "FILE": "SRC-PY-GUIDE-ENGINEERING",
    "OOP": "SRC-PY-GUIDE-ENGINEERING",
}


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source_file:
        record = yaml.safe_load(source_file)
    if not isinstance(record, dict):
        raise ValueError(f"{path} must contain one mapping")
    return record


def dump(path: Path, record: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(record, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def as_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def source_for(concept: dict[str, Any]) -> str | None:
    if concept.get("course") != "python":
        return None
    concept_id = str(concept.get("id", ""))
    parts = concept_id.split("-")
    return PYTHON_SOURCE_BY_PREFIX.get(parts[1]) if len(parts) > 2 else None


def public_example(concept: dict[str, Any], course_root: Path) -> str | None:
    for exercise_id in as_strings(concept.get("assessment_ids")):
        exercise_path = course_root / "exercises" / f"{exercise_id}.yaml"
        if not exercise_path.exists():
            continue
        exercise = load(exercise_path)
        evaluation = exercise.get("evaluation")
        if not isinstance(evaluation, dict):
            continue
        tests = evaluation.get("tests")
        if not isinstance(tests, list):
            continue
        for test in tests:
            if isinstance(test, dict) and test.get("visibility") == "public":
                input_text = str(test.get("input", "")).strip().replace("\n", " / ")
                output_text = str(test.get("expected_output", "")).strip().replace("\n", " / ")
                return f"关联练习示例：输入“{input_text}”时，预期输出“{output_text}”。"
    return None


def enrich_concept(path: Path) -> None:
    concept = load(path)
    concept_id = str(concept["id"])
    title = str(concept["title"])
    lesson_value = concept.get("lesson")
    lesson = dict(lesson_value) if isinstance(lesson_value, dict) else {}
    original_summary = str(lesson.get("summary", "")).strip()
    if len("".join(original_summary.split())) < 60:
        lesson["summary"] = (
            f"{original_summary} 本节围绕“{title}”建立可执行的概念模型：先说明定义、"
            "适用前提和状态变化，再通过最小示例观察行为，最后用正常、边界和失败输入"
            "验证实现。学习结果以关联练习和确定性测试为准。"
        )

    detail = CORE_DETAILS.get(concept_id)
    if detail:
        lesson["key_points"] = list(detail.key_points)
        lesson["examples"] = list(detail.examples)
        lesson["common_mistakes"] = list(detail.mistakes)
    else:
        key_points = as_strings(lesson.get("key_points"))
        if len(key_points) < 3:
            key_points = [
                original_summary,
                f"使用“{title}”时必须写清输入、状态和失败条件，不能只记语法或模板。",
                f"通过“{title}”的关联练习分别验证常规输入、边界输入和错误输入。",
            ]
        examples = as_strings(lesson.get("examples"))
        if not examples:
            exercise_example = public_example(concept, path.parents[1])
            examples = [
                exercise_example
                or f"示例：为“{title}”写出一个最小正常样例和一个边界样例，并逐步记录状态变化。"
            ]
        mistakes = [
            item
            for item in as_strings(lesson.get("common_mistakes"))
            if item not in TEMPLATE_MISTAKES
        ]
        if len(mistakes) < 2:
            mistakes.extend(
                [
                    f"忽略“{title}”的适用前提，直接套用结论或代码模板。",
                    f"完成“{title}”实现后只检查一个正常样例，没有验证边界和失败路径。",
                ]
            )
        lesson["key_points"] = key_points[:4]
        lesson["examples"] = examples[:2]
        lesson["common_mistakes"] = list(dict.fromkeys(mistakes))[:3]

    concept["lesson"] = lesson
    source_id = source_for(concept)
    source_refs = as_strings(concept.get("source_refs"))
    if source_id and source_id not in source_refs:
        source_refs.append(source_id)
        concept["source_refs"] = source_refs
    concept["version"] = max(int(concept.get("version", 1)), 2)
    concept["status"] = "draft"
    dump(path, concept)


def main() -> int:
    count = 0
    for course_id in COURSES:
        for path in sorted((PACKS / course_id / "concepts").glob("*.yaml")):
            enrich_concept(path)
            count += 1
    print(f"Enriched {count} concept cards; all records remain draft for human review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
