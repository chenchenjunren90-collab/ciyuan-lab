import json, csv, re
from pathlib import Path

D = Path(r"C:\Users\32872\Desktop\挑战杯国赛\ciyuan-lab\training\python_tutor\v1\candidates")

# 1) 程序化检查 JSONL：JSON 合法性、字段、引用
violations = {}
with open(D/"sharegpt-python-tutor-v1.jsonl", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line: continue
        rec = json.loads(line)
        conv = rec["conversations"]
        human = conv[1]["value"]
        gpt = conv[2]["value"]
        try:
            h = json.loads(human)
        except Exception as e:
            violations[i] = [f"human 非 JSON: {e}"]
            continue
        evidence_ids = {c["chunk_id"] for c in h.get("evidence", [])}
        probs = []
        try:
            g = json.loads(gpt)
        except Exception as e:
            probs.append(f"gpt 非严格 JSON: {e}")
            violations[i] = probs
            continue
        if set(g.keys()) != {"answer", "citation_chunk_ids"}:
            probs.append(f"gpt 字段不是恰好 answer+citation_chunk_ids: {sorted(g.keys())}")
        if not isinstance(g.get("answer"), str) or not g["answer"].strip():
            probs.append("answer 为空或非字符串")
        cids = g.get("citation_chunk_ids")
        if not isinstance(cids, list):
            probs.append("citation_chunk_ids 不是 list")
        else:
            for cid in cids:
                if cid not in evidence_ids:
                    probs.append(f"引用不存在的 chunk: {cid}")
        if probs:
            violations[i] = probs

print("JSONL 程序化违规条数:", len(violations))
from collections import Counter
kinds = Counter()
for v in violations.values():
    for p in v:
        kinds[p.split(":")[0].split("（")[0][:24]] += 1
for k, c in kinds.most_common():
    print(f"  {k}: {c}")

# 2) CSV 与 JSONL 对齐检查
with open(D/"review-queue.csv", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
print("\nCSV 行数:", len(rows))
# 记录违规的 record_id（按行号映射到 record_id）
rec_ids = [r["record_id"] for r in rows]
viol_rec_ids = {rec_ids[i-1]: v for i, v in violations.items() if i <= len(rec_ids)}
print("违规 record_id 数:", len(viol_rec_ids))

# 3) 关键词扫描（泄露/越界/注入/秘密）
danger = re.compile(r"(密钥|token|api[_-]?key|password|密码|隐藏测试|hidden test|服务器|数据库密码|ssh|绕过|作弊|答案.*直接|完整程序|完整题解|投资建议|股票推荐|医疗|买.*股票)")
scan = {}
for r in rows:
    hits = danger.findall(r["answer"])
    if hits:
        scan[r["record_id"]] = hits
print("\n关键词命中条数:", len(scan))
for rid, hits in list(scan.items())[:20]:
    print(f"  {rid}: {hits}")
