export type TraceKind = "pointer" | "array" | "memory" | "stack" | "queue" | "binary" | "insertion" | "bfs";
export interface TraceFrame { cells: string[]; active: number[]; note: string; variables: Record<string, string>; output: string }
export interface TeachingTrace { title: string; code: string; invariant: string; complexity: string; frames: TraceFrame[] }

export const traceKinds: Record<TraceKind, string> = {
  pointer: "指针交换", array: "数组遍历", memory: "动态内存生命周期", stack: "栈：后进先出",
  queue: "队列：先进先出", binary: "二分查找首个位置", insertion: "插入排序", bfs: "图的广度优先搜索",
};
export function traceForConcept(id: string): TraceKind | null {
  if (id.startsWith("C-PTR")) return "pointer";
  if (id.startsWith("C-ARRAY")) return "array";
  if (id.startsWith("C-MEM")) return "memory";
  if (id.startsWith("DS-STACK")) return "stack";
  if (id.startsWith("DS-QUEUE")) return "queue";
  if (id === "DS-SEARCH-02") return "binary";
  if (id === "DS-SORT-02") return "insertion";
  if (id === "DS-GRAPH-02") return "bfs";
  return null;
}
export function parseTraceInput(text: string): number[] {
  if (!text.trim()) return [];
  const tokens = text.trim().split(/[\s,，]+/);
  if (tokens.length > 12 || tokens.some(token => !/^-?\d+$/.test(token) || Math.abs(Number(token)) > 999)) {
    throw new Error("请输入最多 12 个 -999 至 999 的整数，用空格或逗号分隔。留空可演示空序列。");
  }
  return tokens.map(Number);
}

/** Teaching models only: no eval, no user program execution and no fabricated runtime addresses. */
export function buildTrace(kind: TraceKind, input: number[], target = 2): TeachingTrace {
  if (input.length > 12 || input.some(n => !Number.isInteger(n) || Math.abs(n) > 999) || !Number.isInteger(target) || Math.abs(target) > 999) {
    throw new Error("演示参数超出范围。");
  }
  const frames: TraceFrame[] = [];
  const frame = (cells: (number | string)[], active: number[], note: string, variables: Record<string, string> = {}, output = "") => {
    frames.push({ cells: cells.map(String), active: [...active], note, variables: { ...variables }, output });
  };
  let code = "", invariant = "", complexity = "";
  const values = [...input];
  if (kind === "pointer") {
    if (values.length < 2) throw new Error("指针交换需要至少两个整数，演示使用前两个值。");
    const a = values[0]!, b = values[1]!;
    code = "int a = ..., b = ...;\nint *p = &a, *q = &b;\nint temp = *p;\n*p = *q;\n*q = temp;";
    invariant = "p 始终指向 a，q 始终指向 b；赋值改变对象的值，不改变指针的指向。";
    complexity = "时间 O(1)，额外空间 O(1)。符号 &a / &b 表示地址，不假定真实地址或 int 字节数。";
    frame([a, b], [], "创建两个整数对象。", { p: "尚未声明", q: "尚未声明" });
    frame([a, b], [0, 1], "保存对象地址：p → a，q → b。", { p: "&a", q: "&b" });
    frame([a, b], [0], "先备份 *p，否则覆盖 a 后原值会丢失。", { p: "&a", q: "&b", temp: String(a) });
    frame([b, b], [0], "*p = *q：把 b 的值写入 a。", { p: "&a", q: "&b", temp: String(a) });
    frame([b, a], [1], "*q = temp：把备份值写入 b，交换完成。", { p: "&a", q: "&b", temp: String(a) }, `${b} ${a}`);
  } else if (kind === "memory") {
    code = "int *p = malloc(3 * sizeof *p);\nif (p == NULL) return 1;\np[0] = 7;\nfree(p);\np = NULL;";
    invariant = "只有分配成功且尚未释放时才允许访问。清空 p 不会修复其他指向同一对象的别名。";
    complexity = "固定 3 个 int 的生命周期示意；不对分配器运行时间作保证。";
    frame([], [], "调用 malloc，必须先检查是否返回 NULL。", { p: "分配结果待检查" });
    frame(["未初始化", "未初始化", "未初始化"], [], "本演示沿分配成功分支；内容尚不能读取。", { p: "有效分配块", bytes: "3 × sizeof(int)" });
    frame([7, "未初始化", "未初始化"], [0], "只写入第一个元素，其他元素仍未初始化。", { p: "有效分配块" });
    frame(["已释放", "已释放", "已释放"], [], "free(p) 结束这块分配的生命周期，此后不能解引用。", { p: "不可再使用的旧指针值" });
    frame([], [], "将所有者指针设为 NULL；失败路径不访问内存。", { p: "NULL" });
  } else if (kind === "array") {
    code = "int sum = 0;\nfor (size_t i = 0; i < n; ++i) {\n    sum += a[i];\n}";
    invariant = "第 i 轮前，sum 等于 a[0..i) 的和；只在 i < n 时访问 a[i]。";
    complexity = "时间 O(n)，额外空间 O(1)；这里的小整数输入不会使 int 求和溢出。";
    let sum = 0;
    frame(values, [], "先令 sum = 0，空序列无需访问任何元素。", { i: "0", sum: "0" });
    values.forEach((value, i) => { sum += value; frame(values, [i], `读取 a[${i}] = ${value} 并累加。`, { i: String(i), sum: String(sum) }); });
    frame(values, [], "i == n，循环结束；a[n] 不可读取。", { i: String(values.length), sum: String(sum) }, String(sum));
  } else if (kind === "stack" || kind === "queue") {
    const storage: number[] = [], out: number[] = [];
    code = kind === "stack" ? "for value in values: stack.append(value)\nwhile stack: output(stack.pop())" : "for value in values: queue.append(value)\nwhile queue: output(queue.popleft())";
    invariant = kind === "stack" ? "只从栈顶（右端）入栈和出栈；先检查是否为空。" : "右端入队、左端出队；已入队的先后次序不会改变。";
    complexity = kind === "stack" ? "n 次入栈和出栈总计 O(n)，存储 O(n)；动态数组 append 摊还 O(1)。" : "使用双端队列时每次操作 O(1)，总计 O(n)，存储 O(n)。";
    frame(storage, [], "空结构，不能直接取出元素。");
    values.forEach(value => { storage.push(value); frame(storage, [storage.length - 1], `加入 ${value}。`, { size: String(storage.length) }); });
    while (storage.length) {
      const removed = kind === "stack" ? storage.pop()! : storage.shift()!;
      out.push(removed); frame(storage, [], `取出 ${removed}。`, { size: String(storage.length) }, out.join(" "));
    }
    frame(storage, [], "结构为空，停止取出。", { size: "0" }, out.join(" "));
  } else if (kind === "binary") {
    if (values.some((value, i) => i > 0 && value < values[i - 1]!)) throw new Error("二分查找要求升序输入，请先把序列排好序；系统不会偷偷改变你的输入。");
    code = "left, right = 0, len(a)\nwhile left < right:\n    mid = left + (right - left) // 2\n    if a[mid] < target: left = mid + 1\n    else: right = mid\n# 检查 left < len(a) 且 a[left] == target";
    invariant = "半开区间 [left, right)：左侧均小于 target；right 右侧均大于或等于 target。";
    complexity = "已排序、可随机访问的序列：时间 O(log n)，额外空间 O(1)。";
    let left = 0, right = values.length;
    frame(values, [], "初始化半开区间。", { left: "0", right: String(right), target: String(target) });
    while (left < right) {
      const mid = left + Math.floor((right - left) / 2);
      frame(values, [mid], `比较 a[${mid}] = ${values[mid]} 与 ${target}。`, { left: String(left), right: String(right), mid: String(mid) });
      if (values[mid]! < target) left = mid + 1; else right = mid;
      frame(values, [], "缩小区间；相等时继续收缩右边界以找第一次出现。", { left: String(left), right: String(right) });
    }
    const found = left < values.length && values[left] === target;
    frame(values, found ? [left] : [], found ? "已找到第一个匹配位置。" : "区间收敛，但该位置不等于目标或已越过末尾。", { left: String(left), right: String(right) }, found ? String(left) : "-1");
  } else if (kind === "insertion") {
    code = "for i in range(1, len(a)):\n    key, j = a[i], i - 1\n    while j >= 0 and a[j] > key:\n        a[j + 1] = a[j]\n        j -= 1\n    a[j + 1] = key";
    invariant = "每轮开始时前缀 a[0..i) 已有序；key 单独暂存，严格大于 key 的元素才右移。";
    complexity = "最好 O(n)，最坏 O(n²)，额外空间 O(1)；严格比较可保持稳定性。";
    frame(values, [], "从第二个元素开始，把它插入前面的有序部分。");
    for (let i = 1; i < values.length; i++) {
      const key = values[i]!; let j = i - 1;
      frame(values, [i], `暂存 key = ${key}。`, { i: String(i), key: String(key) });
      while (j >= 0 && values[j]! > key) {
        values[j + 1] = values[j]!;
        frame(values, [j, j + 1], "右移一个较大的元素；重复值是中间状态，key 保存在临时变量中。", { j: String(j), key: String(key) }); j--;
      }
      values[j + 1] = key; frame(values, [j + 1], "把 key 放入空出的位置。", { sortedPrefix: String(i + 1) });
    }
    frame(values, [], "排序完成。", {}, values.join(" "));
  } else {
    // Fixed graph contains a cycle and a disconnected vertex, making boundaries visible.
    const graph = [[1, 2], [0, 3], [0, 3], [1, 2], []];
    const queue = [0], visited = new Set([0]), order: number[] = [];
    const distances = [0, -1, -1, -1, -1];
    code = "queue = deque([0]); seen = {0}\nwhile queue:\n    u = queue.popleft()\n    for v in graph[u]:\n        if v not in seen:\n            seen.add(v)\n            queue.append(v)";
    invariant = "顶点在入队时标记；每个可达顶点最多入队一次。队列按到起点的边数分层。";
    complexity = "邻接表时间 O(V + E)，额外空间 O(V)；固定邻接顺序 0:[1,2], 1:[0,3], 2:[0,3], 3:[1,2], 4:[]。";
    const snapshot = (active: number[], note: string) => frame(graph.map((_, i) => `${i}: ${visited.has(i) ? "已发现" : "未发现"}`), active, note, { queue: queue.join(" → ") || "空", distance: distances.join(", ") }, order.join(" "));
    snapshot([0], "从 0 出发，先标记再入队；4 是孤立顶点。");
    while (queue.length) {
      const u = queue.shift()!; order.push(u); snapshot([u], `出队并访问 ${u}。`);
      for (const v of graph[u]!) if (!visited.has(v)) {
        visited.add(v); distances[v] = distances[u]! + 1; queue.push(v); snapshot([v], `发现 ${v}，立即标记后入队，防止环导致重复访问。`);
      }
    }
    snapshot([], "队列为空。4 不可达，距离为 -1；本次只遍历起点所在连通分量。");
  }
  return { title: traceKinds[kind], code, invariant, complexity, frames };
}
