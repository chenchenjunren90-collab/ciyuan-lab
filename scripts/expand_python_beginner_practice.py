# ruff: noqa: E501
"""Expand the Python MVP with Chinese beginner-friendly after-class practice.

The exercise catalog is deliberately explicit and reviewable.  Open resources
inform the skill sequence and test boundaries, while prompts, scaffolding and
examples are rewritten for this project instead of being copied verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACK = ROOT / "course_packs" / "python"
CONCEPTS = PYTHON_PACK / "concepts"
EXERCISES = PYTHON_PACK / "exercises"

SOURCE_REFS = [
    "SRC-PY-GUIDE-CURRICULUM",
    "SRC-PY-EXERCISM-TRACK",
    "SRC-PY-INTERACTIVE-TUTORIALS",
]


@dataclass(frozen=True)
class Task:
    concept_id: str
    title: str
    prompt: str
    starter_code: str
    public_cases: tuple[tuple[str, str, str], ...]
    hidden_cases: tuple[tuple[str, str, str], ...]
    input_format: str
    output_format: str
    constraints: tuple[str, ...]
    scaffolding: tuple[str, ...]
    source_scope: str
    card_problem: str
    card_code: str
    checkpoint: str
    reflection: str
    exercise_type: str = "code"
    difficulty: str = "beginner"
    estimated_minutes: int = 15

    @property
    def exercise_id(self) -> str:
        return f"{self.concept_id}-H1"


TASKS = (
    Task(
        "PY-BASE-01",
        "课后练习：向新同学问好",
        "读取一行姓名，输出“你好，姓名！”。姓名两侧可能有空格，输出前需要去掉这些空格。",
        'name = input()\n# 去掉姓名两侧的空格，再按指定格式输出\n',
        (("public-normal", "小词\n", "你好，小词！\n"),),
        (("hidden-spaces", "  小元  \n", "你好，小元！\n"),),
        "一行文本，表示姓名。",
        "一行问候语，格式必须为：你好，姓名！",
        ("姓名去除首尾空格后至少包含 1 个字符", "不得输出额外提示文字"),
        ("先用 input() 读取字符串", "使用 strip() 处理首尾空格", "使用 f-string 组合最终文本"),
        "concept: basics / practice: hello-world",
        "先在脚本中输出一句固定的欢迎语。",
        'message = "欢迎来到 Python"\nprint(message)\n',
        "如果把 print 写在引号里面，Python 会把它当作指令还是普通文本？",
        "程序成功运行只是第一步，还要逐字核对输出中的中文标点。",
        estimated_minutes=10,
    ),
    Task(
        "PY-BASE-02",
        "课后练习：整理个人信息",
        "读取由空格分隔的姓名、年龄和身高（米），输出“姓名:...;年龄:...;身高:...”；身高保留 2 位小数。",
        'name, age_text, height_text = input().split()\n# 转换类型并格式化输出\n',
        (("public-normal", "小词 18 1.72\n", "姓名:小词;年龄:18;身高:1.72\n"),),
        (("hidden-format", "小元 20 1.8\n", "姓名:小元;年龄:20;身高:1.80\n"),),
        "一行三个字段：姓名 年龄 身高。",
        "按指定字段顺序输出，身高固定保留 2 位小数。",
        ("年龄是非负整数", "身高是可以转换为 float 的正数"),
        ("先 split() 得到三个字符串", "年龄用 int()，身高用 float()", "使用 :.2f 控制小数位数"),
        "concept: basics / tutorial: Variables and Types",
        "把字符串形式的年龄转换成整数后加一。",
        'age_text = "18"\nage = int(age_text)\nprint(age + 1)\n',
        "input() 返回的年龄为什么不能直接和整数 1 相加？",
        "变量名应表达含义；转换前后的值最好使用不同名字，便于排错。",
    ),
    Task(
        "PY-BASE-03",
        "课后练习：整除与余数",
        "读取两个整数 a 和 b（b 大于 0），输出 a 整除 b 的商和余数，中间用一个空格分隔。",
        'a, b = map(int, input().split())\n# 输出整除结果与余数\n',
        (("public-normal", "17 5\n", "3 2\n"),),
        (("hidden-exact", "20 4\n", "5 0\n"), ("hidden-small", "3 8\n", "0 3\n")),
        "一行两个整数 a b。",
        "一行两个整数：商 余数。",
        ("b > 0", "使用整数运算，不输出小数"),
        ("// 得到整除的商", "% 得到余数", "用 a == (a // b) * b + a % b 自检"),
        "concept: basics / operators",
        "计算 11 除以 4 的商和余数。",
        'a, b = 11, 4\nprint(a // b, a % b)\n',
        "运算符 / 与 // 的结果类型和含义有什么不同？",
        "看到“整除”和“余数”时，先确认题目是否允许负数以及除数能否为零。",
    ),
    Task(
        "PY-BASE-04",
        "课后 Debug：修好两数求和",
        "下面程序想读取两个整数并输出它们的和，但当前代码会报错或得到错误结果。请修复代码。",
        'a, b = input()\nprint(a + b)\n',
        (("public-positive", "3 5\n", "8\n"),),
        (("hidden-negative", "-2 7\n", "5\n"), ("hidden-zero", "0 0\n", "0\n")),
        "一行两个整数。",
        "输出两个整数的和。",
        ("输入以空格分隔", "不得拼接字符串"),
        ("观察解包时右侧有几个值", "先 split() 再转换为整数", "用负数测试，排除字符串拼接"),
        "concept: basics / input-output",
        "读取一个整数并输出它的两倍。",
        'number = int(input())\nprint(number * 2)\n',
        "为什么 input().split() 之后仍然需要 int()？",
        "调试输入问题时，把“读取、拆分、转换、计算、输出”分成五步检查。",
        exercise_type="debug",
    ),
    Task(
        "PY-BASE-05",
        "课后练习：判断学习状态",
        "读取 0 到 100 的整数分数。85 分及以上输出“优秀”，60 到 84 分输出“合格”，其余输出“需巩固”。",
        'score = int(input())\n# 按从严格到宽松的顺序判断\n',
        (("public-excellent", "85\n", "优秀\n"), ("public-pass", "60\n", "合格\n")),
        (("hidden-review", "59\n", "需巩固\n"), ("hidden-high", "100\n", "优秀\n")),
        "一个 0 到 100 的整数。",
        "输出优秀、合格或需巩固之一。",
        ("0 <= score <= 100", "边界 60 和 85 必须归入正确区间"),
        ("先写出三个互斥区间", "从 85 分开始判断，避免宽条件遮蔽", "分别测试 59、60、84、85"),
        "concept: conditionals / practice: grade mapping",
        "根据温度判断是否需要带外套。",
        'temperature = 12\nif temperature < 15:\n    print("带外套")\nelse:\n    print("无需外套")\n',
        "如果先判断 score >= 60，再判断 score >= 85，会发生什么？",
        "条件题最容易错在边界；编码前先把每个区间写在纸上。",
    ),
    Task(
        "PY-BASE-06",
        "课后 Debug：让计数循环停下来",
        "程序应计算 1 到 n 的整数和，但它没有正确更新循环变量。请修复并输出结果。",
        'n = int(input())\ntotal = 0\ni = 1\nwhile i <= n:\n    total += i\nprint(total)\n',
        (("public-five", "5\n", "15\n"),),
        (("hidden-one", "1\n", "1\n"), ("hidden-ten", "10\n", "55\n")),
        "一个正整数 n。",
        "输出 1 到 n 的整数和。",
        ("1 <= n <= 10000", "循环必须在时间限制内结束"),
        ("找出 while 条件依赖的变量", "确认循环体会让该变量靠近终止条件", "用 n=1 检查是否执行一次"),
        "concept: loops / while",
        "用 while 输出 1、2、3。",
        'i = 1\nwhile i <= 3:\n    print(i)\n    i += 1\n',
        "循环体中的哪一步保证条件最终会变成 False？",
        "while 循环应同时检查初始化、继续条件、状态更新三处。",
        exercise_type="debug",
    ),
    Task(
        "PY-BASE-07",
        "课后练习：累加偶数",
        "读取正整数 n，计算并输出 1 到 n（包含 n）之间所有偶数的和。",
        'n = int(input())\ntotal = 0\n# 使用 for 与 range 完成累加\n',
        (("public-six", "6\n", "12\n"),),
        (("hidden-one", "1\n", "0\n"), ("hidden-ten", "10\n", "30\n")),
        "一个正整数 n。",
        "一个整数，表示偶数之和。",
        ("1 <= n <= 100000", "range 的停止位置不包含在序列中"),
        ("可以让 range 从 2 开始、步长为 2", "停止位置需要写成 n + 1", "用奇数 n 检查最后一个偶数"),
        "concept: loops / for-range",
        "输出 0 到 4。",
        'for number in range(5):\n    print(number)\n',
        "range(2, n + 1, 2) 中为什么需要 n + 1？",
        "使用 range 前先写出期望得到的前三项和最后一项。",
    ),
    Task(
        "PY-BASE-08",
        "课后 Debug：用循环 else 判断质数",
        "程序应判断 n 是否为质数。请修复 break 与循环 else 的位置或输出，使质数输出“是质数”，否则输出“不是质数”。",
        'n = int(input())\nfor divisor in range(2, n):\n    if n % divisor == 0:\n        print("是质数")\n        break\nelse:\n    print("不是质数")\n',
        (("public-prime", "7\n", "是质数\n"), ("public-composite", "9\n", "不是质数\n")),
        (("hidden-two", "2\n", "是质数\n"), ("hidden-even", "12\n", "不是质数\n")),
        "一个不小于 2 的整数 n。",
        "输出是质数或不是质数。",
        ("2 <= n <= 10000", "循环 else 只在没有执行 break 时运行"),
        ("找到因数时说明不是质数", "没有找到因数才进入循环 else", "单独测试 n=2，此时循环体不会执行"),
        "concept: loop-control / loop-else",
        "在列表中找到第一个负数后停止。",
        'for value in [3, 2, -1, -4]:\n    if value < 0:\n        print(value)\n        break\n',
        "当 n=2 时 range(2, n) 为空，循环 else 会不会执行？",
        "循环 else 的含义是“正常遍历完”，不是普通 if 的 else。",
        exercise_type="debug",
        difficulty="intermediate",
        estimated_minutes=20,
    ),
    Task(
        "PY-BASE-09",
        "课后练习：转换并格式化金额",
        "读取一个可能为负的小数，输出它的绝对值并固定保留 2 位小数。",
        'text = input()\n# 转成数值、取绝对值并格式化\n',
        (("public-negative", "-3.14159\n", "3.14\n"),),
        (("hidden-integer", "2\n", "2.00\n"), ("hidden-positive", "9.876\n", "9.88\n")),
        "一行可转换为 float 的数字文本。",
        "绝对值，固定保留 2 位小数。",
        ("输入绝对值不超过 1000000", "必须显示末尾的零"),
        ("float() 完成转换", "abs() 求绝对值", "f-string 的 :.2f 控制显示格式"),
        "concept: builtins / numeric conversion",
        "把文本 3.5 转成浮点数并取绝对值。",
        'value = float("-3.5")\nprint(abs(value))\n',
        "round(value, 2) 与格式化为两位小数在显示效果上一定相同吗？",
        "计算精度和显示格式是两个问题；题目要求“保留两位”时要控制输出格式。",
    ),
    Task(
        "PY-BASE-10",
        "课后综合：温度统计",
        "第一行读取整数 n，第二行读取 n 个整数温度。输出最低温、最高温和平均温度，三项以空格分隔，平均值保留 1 位小数。",
        'n = int(input())\ntemperatures = list(map(int, input().split()))\n# 校验数量后完成统计\n',
        (("public-normal", "4\n12 18 15 11\n", "11 18 14.0\n"),),
        (("hidden-one", "1\n-3\n", "-3 -3 -3.0\n"), ("hidden-mixed", "3\n-2 0 5\n", "-2 5 1.0\n")),
        "第一行 n；第二行 n 个空格分隔的整数。",
        "最低温 最高温 平均温度。",
        ("1 <= n <= 1000", "第二行数字数量等于 n"),
        ("先完成输入转换，再做统计", "min/max 求边界，sum/n 求平均", "用 n=1 检查最小输入"),
        "curriculum: review-python-basics / small project",
        "统计三个数字的最大值和平均值。",
        'values = [2, 5, 8]\nprint(max(values), sum(values) / len(values))\n',
        "当列表只有一个元素时，最低、最高和平均值分别是什么？",
        "综合题应分成输入、校验、处理、输出四段逐步验证。",
        difficulty="intermediate",
        estimated_minutes=20,
    ),
    Task(
        "PY-STR-01",
        "课后练习：生成节奏口令",
        "读取一个不含空格的单词和重复次数 n，用连字符连接并输出该单词 n 次。",
        'word, count_text = input().split()\n# 例如 ha 3 输出 ha-ha-ha\n',
        (("public-three", "ha 3\n", "ha-ha-ha\n"),),
        (("hidden-one", "go 1\n", "go\n"), ("hidden-four", "py 4\n", "py-py-py-py\n")),
        "一行：单词 重复次数。",
        "用连字符连接的重复文本。",
        ("1 <= n <= 20", "开头和结尾不能多出连字符"),
        ("先构造包含 n 个单词的序列", "使用 '-'.join(...) 避免多余分隔符", "测试 n=1"),
        "tutorial: Basic String Operations",
        "拼接姓和名，中间留一个空格。",
        'family_name = "陈"\ngiven_name = "小词"\nprint(family_name + " " + given_name)\n',
        "为什么用 join 比在循环中手动判断最后一个连字符更简单？",
        "拼接文本时要把内容和分隔符分别想清楚。",
    ),
    Task(
        "PY-STR-02",
        "课后练习：截取文本片段",
        "第一行读取字符串，第二行读取 start 和 end，输出字符串的 s[start:end]。",
        'text = input()\nstart, end = map(int, input().split())\n# 输出半开区间切片\n',
        (("public-middle", "python\n1 4\n", "yth\n"),),
        (("hidden-start", "hello\n0 2\n", "he\n"), ("hidden-empty", "abc\n2 2\n", "\n")),
        "第一行字符串；第二行两个整数 start end。",
        "输出左闭右开的字符串切片。",
        ("0 <= start <= end <= 字符串长度", "end 位置的字符不包含在结果中"),
        ("索引从 0 开始", "切片写成 text[start:end]", "用 start == end 检查空切片"),
        "tutorial: Basic String Operations / slicing",
        "取出单词 python 的前三个字符。",
        'word = "python"\nprint(word[0:3])\n',
        "s[1:4] 包含下标 4 对应的字符吗？",
        "切片使用半开区间；长度通常等于 end - start。",
    ),
    Task(
        "PY-STR-03",
        "课后练习：清理不规则空格",
        "读取一行文本，去掉首尾空格，把单词之间的连续空白统一为一个空格，并将所有字母转为小写。",
        'text = input()\n# split() 后再 join()，最后统一大小写\n',
        (("public-spaces", "  PyThOn   IS fun  \n", "python is fun\n"),),
        (("hidden-clean", "Already clean\n", "already clean\n"), ("hidden-tabs", "A\tB   C\n", "a b c\n")),
        "一行文本，单词之间可能包含多个空格或制表符。",
        "规范化后的小写文本。",
        ("输入至少包含一个非空白字符", "输出首尾不得有空格"),
        ("不传参数的 split() 会处理连续空白", "使用 ' '.join(words) 重新连接", "使用 lower() 统一大小写"),
        "tutorial: Basic String Operations / methods",
        "将姓名两侧空格去掉并转成大写。",
        'name = "  xiao ci  "\nprint(name.strip().upper())\n',
        "为什么直接 replace('  ', ' ') 可能无法一次处理三个以上连续空格？",
        "字符串清洗应先定义规则，再组合最少且可测试的方法。",
    ),
    Task(
        "PY-TUPLE-01",
        "课后练习：轮换三个值",
        "读取三个整数 a、b、c，使用打包与解包思路输出 c、a、b。",
        'a, b, c = map(int, input().split())\n# 轮换三个变量\n',
        (("public-normal", "1 2 3\n", "3 1 2\n"),),
        (("hidden-negative", "-1 0 7\n", "7 -1 0\n"),),
        "一行三个整数。",
        "按 c a b 的顺序输出。",
        ("必须保持每个值不变", "输出字段以单个空格分隔"),
        ("右侧先形成一个三元素元组", "左侧按新顺序接收", "画箭头确认每个旧值去向"),
        "tutorial: Tuples",
        "交换两个变量的值。",
        'left, right = 1, 2\nleft, right = right, left\nprint(left, right)\n',
        "单元素元组为什么需要写成 (value,)？",
        "元组解包要求左右元素数量一致。",
    ),
    Task(
        "PY-SET-01",
        "课后练习：统计唯一标签",
        "读取一行空格分隔的标签，第一行输出不同标签的数量，第二行按字典序输出去重后的标签。",
        'tags = input().split()\n# 使用集合去重，再排序以保证输出稳定\n',
        (("public-duplicates", "pear apple pear\n", "2\napple pear\n"),),
        (("hidden-unique", "c b a\n", "3\na b c\n"), ("hidden-one", "python\n", "1\npython\n")),
        "一行一个或多个空格分隔的标签。",
        "第一行数量；第二行排序后的唯一标签。",
        ("标签区分大小写", "展示前必须排序，不能依赖集合内部顺序"),
        ("set(tags) 完成去重", "sorted(...) 产生稳定顺序", "len(...) 计算唯一数量"),
        "tutorial: Sets",
        "找出两组课程名称的共同项。",
        'left = {"Python", "C"}\nright = {"Python", "数据结构"}\nprint(left & right)\n',
        "集合可以保证每次迭代的显示顺序都相同吗？",
        "集合适合成员判断和去重；需要展示时通常还要排序。",
    ),
    Task(
        "PY-LIST-01",
        "课后练习：安全访问列表",
        "第一行读取若干整数，第二行读取索引 i。若 i 在 Python 合法索引范围内，输出对应元素；否则输出“越界”。",
        'numbers = list(map(int, input().split()))\nindex = int(input())\n# 同时考虑正索引和负索引\n',
        (("public-positive", "10 20 30\n1\n", "20\n"), ("public-negative", "10 20 30\n-1\n", "30\n")),
        (("hidden-left-bound", "5 6\n-2\n", "5\n"), ("hidden-out", "5 6\n2\n", "越界\n")),
        "第一行非空整数列表；第二行整数索引。",
        "对应元素或越界。",
        ("列表长度至少为 1", "合法范围为 -len(numbers) 到 len(numbers)-1"),
        ("正索引上界是 len(numbers)-1", "负索引下界是 -len(numbers)", "先判断范围再访问，避免异常"),
        "concept: lists / indexing",
        "访问列表中的第一个和最后一个元素。",
        'values = [10, 20, 30]\nprint(values[0], values[-1])\n',
        "长度为 3 的列表中，索引 -3 和 2 分别指向哪里？",
        "访问前先把合法索引范围写出来，尤其要考虑负索引。",
    ),
    Task(
        "PY-LIST-02",
        "课后 Debug：正确排序列表",
        "程序应把输入整数升序输出，但错误地把 sort() 的返回值当成新列表。请修复。",
        'numbers = list(map(int, input().split()))\nresult = numbers.sort()\nprint(*result)\n',
        (("public-mixed", "3 1 2\n", "1 2 3\n"),),
        (("hidden-duplicates", "4 2 4 1\n", "1 2 4 4\n"), ("hidden-one", "7\n", "7\n")),
        "一行一个或多个整数。",
        "升序排列后的整数，以空格分隔。",
        ("保留重复元素", "不得输出列表方括号和逗号"),
        ("list.sort() 原地修改列表并返回 None", "可以排序后直接输出 numbers", "也可以使用 sorted(numbers) 得到新列表"),
        "concept: list methods / sorting",
        "在列表末尾添加一个元素。",
        'items = [1, 2]\nitems.append(3)\nprint(items)\n',
        "append()、sort() 等原地方法通常返回什么？",
        "遇到 NoneType 报错时，检查是否误用了原地方法的返回值。",
        exercise_type="debug",
    ),
    Task(
        "PY-LIST-03",
        "课后作业：筛选并转为大写",
        "读取一行由空格分隔的单词，保留长度不少于 3 的单词并转为大写，按原顺序以空格分隔输出。",
        'words = input().split()\n# 使用列表推导式完成筛选和转换\n',
        (("public-mixed", "a sun python go\n", "SUN PYTHON\n"),),
        (("hidden-case", "Data ai loop If\n", "DATA LOOP\n"),),
        "一行空格分隔的单词。",
        "筛选并转为大写后的单词，以空格分隔。",
        ("保持原顺序", "长度恰好为 3 的单词应保留", "没有结果时只输出空行"),
        ("先用普通循环写出筛选规则", "把 append 的值放到推导式表达式位置", "把长度判断写到 if 位置"),
        "concept: list comprehensions / filtering",
        "生成 0 到 4 的平方列表。",
        'squares = [number * number for number in range(5)]\nprint(squares)\n',
        "列表推导式中，转换表达式和过滤条件分别位于什么位置？",
        "推导式应保持一眼可读；条件过多时改回普通循环。",
        difficulty="intermediate",
    ),
    Task(
        "PY-DICT-01",
        "课后练习：统计单词次数",
        "读取一行单词，统计每个单词出现次数，并按单词字典序逐行输出“单词:次数”。",
        'words = input().split()\ncounts = {}\n# 使用字典累计次数，再按键排序输出\n',
        (("public-normal", "apple banana apple\n", "apple:2\nbanana:1\n"),),
        (("hidden-one", "python\n", "python:1\n"), ("hidden-mixed", "b a b c a b\n", "a:2\nb:3\nc:1\n")),
        "一行一个或多个空格分隔的单词。",
        "按键排序后，每行输出 单词:次数。",
        ("单词区分大小写", "每个单词只输出一行"),
        ("使用 counts.get(word, 0) 处理首次出现", "每次出现加 1", "遍历 sorted(counts) 保证稳定顺序"),
        "concept: dicts / practice: inventory-style counting",
        "用字典保存两门课程的成绩。",
        'scores = {"Python": 90, "C": 85}\nprint(scores.get("Python", 0))\n',
        "直接写 counts[word] += 1 时，单词第一次出现会发生什么？",
        "字典累计题的核心是为“尚不存在的键”设计默认值。",
        estimated_minutes=20,
    ),
    Task(
        "PY-DICT-02",
        "课后练习：按成绩排序记录",
        "第一行读取记录数 n，随后 n 行每行包含姓名和整数成绩。按成绩从高到低排序；同分按姓名字典序排序，逐行输出“姓名 成绩”。",
        'n = int(input())\nrecords = {}\nfor _ in range(n):\n    name, score_text = input().split()\n    records[name] = int(score_text)\n# 使用 items() 得到键值对并排序\n',
        (("public-normal", "3\n小词 88\n小元 95\n小码 88\n", "小元 95\n小码 88\n小词 88\n"),),
        (("hidden-one", "1\nA 60\n", "A 60\n"), ("hidden-tie", "3\nC 90\nA 90\nB 80\n", "A 90\nC 90\nB 80\n")),
        "第一行 n；随后 n 行：姓名 成绩。",
        "按指定规则排序后的姓名和成绩。",
        ("1 <= n <= 100", "姓名互不重复", "0 <= 成绩 <= 100"),
        ("records.items() 产生 (姓名, 成绩)", "排序键可写成 (-成绩, 姓名)", "输出时对元组解包"),
        "concept: dict iteration / sorting records",
        "同时遍历字典的键和值。",
        'scores = {"小词": 88, "小元": 95}\nfor name, score in scores.items():\n    print(name, score)\n',
        "为什么排序键中的成绩要取负数？",
        "多条件排序时，先明确每个字段是升序还是降序。",
        difficulty="intermediate",
        estimated_minutes=25,
    ),
)


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def _test_case(case: tuple[str, str, str], visibility: str) -> dict[str, str]:
    case_id, input_text, output_text = case
    return {
        "id": case_id,
        "visibility": visibility,
        "input": input_text,
        "expected_output": output_text,
    }


def _extensions(task: Task) -> dict[str, Any]:
    first_public = task.public_cases[0]
    return {
        "learning_stage": "after_class",
        "audience": "chinese_beginner",
        "scaffolding": list(task.scaffolding),
        "input_format": task.input_format,
        "output_format": task.output_format,
        "constraints": list(task.constraints),
        "public_examples": [
            {
                "input": first_public[1],
                "expected_output": first_public[2],
                "explanation": "先按输入格式拆分数据，再逐步应用本节知识点；输出需与格式完全一致。",
            }
        ],
        "reflection_prompt": task.reflection,
        "source_adaptation": {
            "source_id": "SRC-PY-EXERCISM-TRACK",
            "source_scope": task.source_scope,
            "method": "保留能力目标与边界测试思路，使用中文重写题面、提示、样例和测试。",
        },
    }


def _exercise(task: Task) -> dict[str, Any]:
    return {
        "id": task.exercise_id,
        "title": task.title,
        "course": "python",
        "schema_version": "0.1.0",
        "version": 1,
        "type": task.exercise_type,
        "difficulty": task.difficulty,
        "estimated_minutes": task.estimated_minutes,
        "concept_ids": [task.concept_id],
        "prompt": task.prompt,
        "source_refs": SOURCE_REFS,
        "evaluation": {
            "mode": "tests",
            "starter_code": task.starter_code,
            "runtime": {
                "language": "python",
                "version": "3.11",
                "entrypoint": "main.py",
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "output_limit_kb": 64,
                "network_access": False,
                "filesystem_access": "isolated",
            },
            "tests": [
                *(_test_case(case, "public") for case in task.public_cases),
                *(_test_case(case, "hidden") for case in task.hidden_cases),
            ],
        },
        "extensions": _extensions(task),
        "status": "draft",
    }


def _enrich_concept(task: Task) -> None:
    path = CONCEPTS / f"{task.concept_id}.yaml"
    concept = _load(path)
    assessment_ids = concept.setdefault("assessment_ids", [])
    if task.exercise_id not in assessment_ids:
        assessment_ids.append(task.exercise_id)
    for source_id in SOURCE_REFS:
        if source_id not in concept["source_refs"]:
            concept["source_refs"].append(source_id)
    lesson = concept["lesson"]
    lesson.setdefault(
        "learning_sequence",
        [
            {"title": "先建立直觉", "content": lesson["summary"]},
            {
                "title": "跟着示例做",
                "content": f"先运行示例并逐行观察变量变化，再替换一个输入重新预测结果。示例任务：{task.card_problem}",
            },
            {
                "title": "独立完成课后练习",
                "content": f"完成 {task.exercise_id}。第一次只看题面；遇到困难时按顺序打开提示，不直接查看完整答案。",
            },
        ],
    )
    lesson.setdefault(
        "worked_example",
        {
            "problem": task.card_problem,
            "steps": [
                "写清输入、处理和输出三部分。",
                "先完成最小可运行代码，再用一个正常输入验证。",
                "补充边界输入，确认输出格式与预期一致。",
            ],
            "code": task.card_code,
            "reflection": task.reflection,
        },
    )
    lesson.setdefault(
        "checkpoint",
        {
            "prompt": task.checkpoint,
            "guidance": "先用自己的话回答；如果不确定，回到示例逐行运行，再完成随堂检查和课后练习。",
        },
    )
    _write(path, concept)


def _adapt_existing_list_comprehension_task(task: Task) -> None:
    path = EXERCISES / f"{task.exercise_id}.yaml"
    exercise = _load(path)
    exercise["extensions"] = _extensions(task)
    for source_id in SOURCE_REFS:
        if source_id not in exercise["source_refs"]:
            exercise["source_refs"].append(source_id)
    _write(path, exercise)


def main() -> None:
    EXERCISES.mkdir(parents=True, exist_ok=True)
    for task in TASKS:
        _enrich_concept(task)
        target = EXERCISES / f"{task.exercise_id}.yaml"
        if target.exists():
            if task.concept_id != "PY-LIST-03":
                raise FileExistsError(f"refusing to overwrite existing exercise: {target}")
            _adapt_existing_list_comprehension_task(task)
        else:
            _write(target, _exercise(task))
    print(f"expanded {len(TASKS)} Python beginner knowledge-practice pairs")


if __name__ == "__main__":
    main()
