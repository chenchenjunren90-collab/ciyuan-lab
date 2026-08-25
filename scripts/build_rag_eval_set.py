"""Generate the version-controlled 75-query RAG retrieval evaluation set."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evals" / "rag" / "retrieval-v1.jsonl"

ANSWERABLE: dict[str, dict[str, list[str]]] = {
    "c": {
        "SRC-C-GUIDE-BASE": [
            "C 程序从源文件到可执行程序经历哪些阶段",
            "变量为什么必须在第一次读取前初始化",
            "printf 格式说明符为什么要和实参类型一致",
            "表达式求值时如何处理优先级和短路求值",
        ],
        "SRC-C-GUIDE-CONTROL": [
            "C 语言分支测试为什么要覆盖边界值",
            "循环设计需要明确哪些组成部分",
            "函数怎样通过参数和返回值降低复杂度",
            "递归函数为什么必须有终止条件",
        ],
        "SRC-C-GUIDE-MEMORY": [
            "数组下标和指针移动为什么受存储范围限制",
            "C 字符串为什么必须以空字符终止",
            "动态内存管理为什么要明确所有权和释放点",
            "释放后使用指针会造成什么问题",
        ],
        "SRC-C-GUIDE-ENGINEERING": [
            "C 项目如何分离头文件公开声明与源文件实现",
            "调试 C 程序时怎样从最小失败输入开始",
            "C 程序测试应覆盖哪些正常边界与错误路径",
        ],
    },
    "python": {
        "SRC-PY-GUIDE-BASE": [
            "Python 变量名绑定对象是什么意思",
            "选择列表集合字典时应考虑顺序唯一性和键值关系",
            "Python 条件和循环为什么要测试边界",
        ],
        "SRC-PY-GUIDE-FUNCTIONS": [
            "Python 函数怎样明确输入输出和副作用",
            "默认参数在什么时候求值",
            "迭代器和生成器怎样避免一次加载全部数据",
        ],
        "SRC-PY-GUIDE-DATA": [
            "Python 数据处理为什么先确认字段类型和缺失约定",
            "数据清洗规则应准备哪些正常边界错误样例",
            "异常数据为什么不能被静默吞掉",
        ],
        "SRC-PY-GUIDE-ENGINEERING": [
            "可维护 Python 项目如何隔离文件和网络副作用",
            "调试 Python 代码为什么先固定失败输入",
            "为什么要增加回归测试防止缺陷再次出现",
        ],
        "SRC-PY-GUIDE-CASE-FALLBACK": [
            "合成经营数据集包含哪些字段",
            "如何练习解析校验清洗聚合和异常报告",
            "虚构经营数据为什么不能用于真实经营判断",
        ],
    },
    "data_structures": {
        "SRC-DS-GUIDE-FOUND": [
            "抽象数据类型与具体实现有什么区别",
            "算法分析为什么先定义输入规模和基本操作",
            "递归算法如何证明终止性",
            "如何用递推式估算递归算法时间成本",
        ],
        "SRC-DS-GUIDE-LINEAR": [
            "顺序表随机访问和中间插入的代价分别是什么",
            "链表为什么通过链接获得局部修改能力",
            "栈为什么是后进先出",
            "队列为什么是先进先出",
        ],
        "SRC-DS-GUIDE-SORTSEARCH": [
            "比较排序算法时要考虑哪些指标",
            "二分查找为什么只适用于有序区间",
            "二分查找如何维护答案所在区间不变式",
            "散列表性能受哪些因素影响",
        ],
        "SRC-DS-GUIDE-TREEGRAPH": [
            "BFS 为什么使用队列按层扩展",
            "DFS 如何沿路径深入图结构",
            "最短路算法为什么依赖边权前提",
        ],
    },
}

NEGATIVE: dict[str, list[str]] = {
    "c": [
        "如何配置 Kubernetes 集群自动扩缩容",
        "Transformer 注意力机制如何训练",
        "中国古代诗词有哪些格律",
        "如何诊断高血压并选择药物",
        "量子纠缠实验怎样设计",
    ],
    "python": [
        "欧盟最新关税政策是什么",
        "如何维修汽车变速箱",
        "莫扎特交响曲的创作背景",
        "建筑抗震规范如何计算",
        "如何种植耐旱小麦",
    ],
    "data_structures": [
        "公司年度审计报告如何出具意见",
        "民法典关于租赁合同如何规定",
        "蛋白质折叠实验有哪些步骤",
        "如何绘制油画人物肖像",
        "卫星轨道如何进行修正",
    ],
}

CROSS_COURSE: dict[str, list[str]] = {
    "c": [
        "Python 默认参数在什么时候求值",
        "Python 生成器如何暂停和恢复",
        "BFS 为什么使用队列",
        "二分查找如何维护区间不变式",
        "散列表冲突如何处理",
    ],
    "python": [
        "C 字符串为什么需要空字符终止",
        "C 动态内存释放后为什么不能使用",
        "栈为什么后进先出",
        "递归算法如何用递推式分析",
        "图的最短路依赖什么边权前提",
    ],
    "data_structures": [
        "Python 变量名怎样绑定对象",
        "Python 默认参数何时求值",
        "C 头文件声明和源文件实现如何分离",
        "C printf 格式说明符如何匹配类型",
        "Python 数据异常为什么不能静默吞掉",
    ],
}


def main() -> int:
    records: list[dict[str, object]] = []
    for course_id, sources in ANSWERABLE.items():
        sequence = 0
        for source_id, queries in sources.items():
            for query in queries:
                sequence += 1
                records.append(
                    {
                        "id": f"{course_id}-a-{sequence:02d}",
                        "course_id": course_id,
                        "query": query,
                        "kind": "answerable",
                        "expected_source_ids": [source_id],
                    }
                )
        for sequence, query in enumerate(NEGATIVE[course_id], start=1):
            records.append(
                {
                    "id": f"{course_id}-u-{sequence:02d}",
                    "course_id": course_id,
                    "query": query,
                    "kind": "unanswerable",
                    "expected_source_ids": [],
                }
            )
        for sequence, query in enumerate(CROSS_COURSE[course_id], start=1):
            records.append(
                {
                    "id": f"{course_id}-x-{sequence:02d}",
                    "course_id": course_id,
                    "query": query,
                    "kind": "cross_course",
                    "expected_source_ids": [],
                }
            )
    if len(records) != 75:
        raise RuntimeError(f"expected 75 records, got {len(records)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} retrieval cases -> {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
