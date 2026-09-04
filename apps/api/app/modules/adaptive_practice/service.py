"""Profile-driven Python problem variants with deterministic hidden tests."""

from __future__ import annotations

import hashlib
import random
import re
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from app.modules.adaptive_practice.models import (
    AdaptiveProblemSubmission,
    GeneratedCodeProblem,
    GeneratedProblemBundle,
    PublicExample,
)
from app.modules.course_content import CourseId
from app.modules.learner_profile.models import LearnerProfile
from app.modules.learner_profile.policy import EvidenceMasteryPolicy
from app.modules.learner_profile.records import LearningEvent
from app.modules.learning_flow.service import LearningStore
from app.modules.practice.models import VerificationResult
from app.modules.practice.ports import CodeTestCase, CodeVerifier

_PROBLEM_ID = re.compile(r"^GEN-PY-([A-Z0-9-]+)-(\d{1,4})-([0-9a-f]{10})$")


class _TemplateBuilder(Protocol):
    def __call__(self, *, problem_id: str, seed: int) -> GeneratedProblemBundle: ...


class AdaptiveProblemService:
    """Choose a weak skill, generate a signed variant, verify it and update mastery."""

    def __init__(self, *, repository: LearningStore, verifier: CodeVerifier) -> None:
        self._repository = repository
        self._verifier = verifier
        self._policy = EvidenceMasteryPolicy()
        self._templates: dict[str, tuple[str, _TemplateBuilder]] = {
            "LIST-SUMMARY": ("PY-LIST-01", _list_summary),
            "DICT-COUNT": ("PY-DICT-01", _dict_count),
            "LIST-FILTER": ("PY-LIST-03", _list_filter),
            "SAFE-PARSE": ("PY-EXC-01", _safe_parse),
        }

    def generate(
        self, *, student_id: str, course_id: CourseId, attempt_index: int
    ) -> GeneratedCodeProblem:
        if course_id != "python":
            raise ValueError("adaptive generated code problems are enabled for Python only")
        if not 1 <= attempt_index <= 9999:
            raise ValueError("attempt_index must be between 1 and 9999")
        profile = self._require_profile(student_id, course_id)
        template_id = self._select_template(profile)
        return self._build(student_id, template_id, attempt_index).public

    async def submit(
        self,
        *,
        student_id: str,
        problem_id: str,
        source_code: str,
    ) -> AdaptiveProblemSubmission:
        if not source_code.strip():
            raise ValueError("source_code must not be empty")
        self._require_profile(student_id, "python")
        template_id, attempt_index = self._parse_problem_id(student_id, problem_id)
        bundle = self._build(student_id, template_id, attempt_index)
        result = await self._verifier.verify(
            "python",
            source_code,
            bundle.tests,
            {"time_limit_ms": 2000, "memory_limit_mb": 128, "output_limit_kb": 64},
        )
        concept_id = bundle.public.concept_ids[0]
        event = LearningEvent(
            event_id=uuid4(),
            schema_version="0.1.0",
            event_type="code.verified",
            occurred_at=datetime.now(UTC),
            student_id=student_id,
            course_id="python",
            course_version="0.1.0",
            knowledge_point_id=concept_id,
            trace_id=problem_id,
            payload={
                "accepted": result.accepted,
                "passed_tests": result.passed_tests,
                "total_tests": result.total_tests,
                "generated_problem_id": problem_id,
                "generator": "deterministic_template_v1",
            },
            evidence_summary="个性化生成题的确定性隐藏测试结果",
        )
        if self._repository.append_event(event):
            self._repository.project_event(event_id=event.event_id, policy=self._policy)
        profile = self._require_profile(student_id, "python")
        next_problem = self.generate(
            student_id=student_id,
            course_id="python",
            attempt_index=min(9999, attempt_index + 1),
        )
        verification = VerificationResult(
            accepted=result.accepted,
            passed_tests=result.passed_tests,
            total_tests=result.total_tests,
            diagnostics=list(result.diagnostics),
        )
        feedback = (
            "新题已通过全部确定性测试，画像已更新，并已生成下一道个性化题目。"
            if result.accepted
            else "尚未通过全部测试。请根据公开示例和分级提示定位边界，再次提交。"
        )
        return AdaptiveProblemSubmission(
            problem=bundle.public,
            verification=verification,
            feedback=feedback,
            profile=profile,
            next_problem=next_problem,
        )

    def _require_profile(self, student_id: str, course_id: CourseId) -> LearnerProfile:
        profile = self._repository.get_profile(student_id=student_id, course_id=course_id)
        if profile is None:
            raise LookupError("learner profile not found; complete diagnostic assessment first")
        return profile

    def _select_template(self, profile: LearnerProfile) -> str:
        states = {item.knowledge_point_id: item for item in profile.mastery}
        candidates: list[tuple[float, int, str]] = []
        for template_id, (concept_id, _) in self._templates.items():
            state = states.get(concept_id)
            candidates.append(
                (
                    state.score if state else 0.5,
                    state.evidence_count if state else 0,
                    template_id,
                )
            )
        candidates.sort()
        return candidates[0][2]

    def _build(
        self, student_id: str, template_id: str, attempt_index: int
    ) -> GeneratedProblemBundle:
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError("unknown generated problem template")
        problem_id, seed = self._identity(student_id, template_id, attempt_index)
        return template[1](problem_id=problem_id, seed=seed)

    def _parse_problem_id(self, student_id: str, problem_id: str) -> tuple[str, int]:
        match = _PROBLEM_ID.fullmatch(problem_id)
        if match is None:
            raise ValueError("invalid generated problem_id")
        template_id, raw_attempt, signature = match.groups()
        attempt_index = int(raw_attempt)
        expected_id, _ = self._identity(student_id, template_id, attempt_index)
        if problem_id != expected_id or signature not in expected_id:
            raise ValueError("generated problem_id does not belong to this learner session")
        return template_id, attempt_index

    @staticmethod
    def _identity(student_id: str, template_id: str, attempt_index: int) -> tuple[str, int]:
        digest = hashlib.sha256(
            f"adaptive-v1:{student_id}:{template_id}:{attempt_index}".encode()
        ).hexdigest()
        signature = digest[:10]
        seed = int(digest[10:26], 16)
        return f"GEN-PY-{template_id}-{attempt_index}-{signature}", seed


def _case(case_id: str, visibility: str, input_text: str, expected: str) -> CodeTestCase:
    return CodeTestCase(
        id=case_id,
        visibility=visibility,  # type: ignore[arg-type]
        input=input_text,
        expected_output=expected,
    )


def _bundle(
    *,
    problem_id: str,
    template_id: str,
    title: str,
    prompt: str,
    concept_id: str,
    constraints: list[str],
    starter_code: str,
    hints: list[str],
    tests: tuple[CodeTestCase, ...],
) -> GeneratedProblemBundle:
    public = next(item for item in tests if item.visibility == "public")
    return GeneratedProblemBundle(
        public=GeneratedCodeProblem(
            problem_id=problem_id,
            title=title,
            prompt=prompt,
            concept_ids=[concept_id],
            difficulty="intermediate",
            constraints=constraints,
            public_examples=[
                PublicExample(input=public.input, expected_output=public.expected_output)
            ],
            starter_code=starter_code,
            hints=hints,
            generation_notice=(
                "题目由项目组确定性模板生成；参数和隐藏测试随学习状态变化，"
                "大模型不参与答案与判题标准生成。"
            ),
        ),
        tests=tests,
        template_id=template_id,
    )


def _list_summary(*, problem_id: str, seed: int) -> GeneratedProblemBundle:
    rng = random.Random(seed)

    def render(values: list[int]) -> tuple[str, str]:
        input_text = f"{len(values)}\n" + " ".join(map(str, values)) + "\n"
        expected = (
            "EMPTY\n"
            if not values
            else f"{len(values)} {sum(values)} {min(values)} {max(values)}\n"
        )
        return input_text, expected

    samples = [[3, -1, 5, 3], [], [rng.randint(-20, 20) for _ in range(9)]]
    tests = tuple(
        _case(f"ls-{index}", "public" if index == 1 else "hidden", *render(values))
        for index, values in enumerate(samples, start=1)
    )
    return _bundle(
        problem_id=problem_id,
        template_id="LIST-SUMMARY",
        title="序列摘要",
        prompt=(
            "读取整数数量 n 和一行整数。若 n=0 输出 EMPTY；否则依次输出元素数量、"
            "总和、最小值和最大值，使用一个空格分隔。"
        ),
        concept_id="PY-LIST-01",
        constraints=["0 ≤ n ≤ 100", "输入整数范围为 -10^4 到 10^4", "输出格式必须精确"],
        starter_code=(
            "n = int(input())\n"
            "values = list(map(int, input().split())) if n else []\n"
            "# 在此完成\n"
        ),
        hints=[
            "先单独处理空列表。",
            "非空列表可以使用 len、sum、min 和 max。",
            "使用一个 print 调用输出四个值。",
        ],
        tests=tests,
    )


def _dict_count(*, problem_id: str, seed: int) -> GeneratedProblemBundle:
    rng = random.Random(seed)
    labels = ["alpha", "beta", "gamma", "delta"]

    def render(values: list[str]) -> tuple[str, str]:
        input_text = f"{len(values)}\n" + "\n".join(values) + "\n"
        counts = {label: values.count(label) for label in sorted(set(values))}
        expected = "".join(f"{label} {count}\n" for label, count in counts.items())
        return input_text, expected

    samples = [
        ["beta", "alpha", "beta", "gamma"],
        [rng.choice(labels) for _ in range(13)],
        ["alpha"],
    ]
    tests = tuple(
        _case(f"dc-{index}", "public" if index == 1 else "hidden", *render(values))
        for index, values in enumerate(samples, start=1)
    )
    return _bundle(
        problem_id=problem_id,
        template_id="DICT-COUNT",
        title="分类计数",
        prompt="读取 n 个分类标签，按标签字典序逐行输出“标签 次数”。",
        concept_id="PY-DICT-01",
        constraints=["1 ≤ n ≤ 200", "标签只含小写英文字母", "每个标签单独占一行"],
        starter_code="n = int(input())\ncounts = {}\n# 在此读取、计数并按键排序输出\n",
        hints=[
            "字典适合保存标签到次数的映射。",
            "读取标签时使用 get(label, 0) 累加。",
            "输出阶段遍历 sorted(counts)。",
        ],
        tests=tests,
    )


def _list_filter(*, problem_id: str, seed: int) -> GeneratedProblemBundle:
    rng = random.Random(seed)

    def render(values: list[int]) -> tuple[str, str]:
        result = [value * value for value in values if value > 0 and value % 2 == 0]
        return " ".join(map(str, values)) + "\n", " ".join(map(str, result)) + "\n"

    samples = [
        [-3, 2, 5, 4, 0, -8],
        [rng.randint(-12, 12) for _ in range(15)],
        [-5, -3, 1, 3],
    ]
    tests = tuple(
        _case(f"lf-{index}", "public" if index == 1 else "hidden", *render(values))
        for index, values in enumerate(samples, start=1)
    )
    return _bundle(
        problem_id=problem_id,
        template_id="LIST-FILTER",
        title="筛选并平方",
        prompt="读取一行整数，只保留正偶数并输出它们的平方，保持原顺序。无结果时输出空行。",
        concept_id="PY-LIST-03",
        constraints=["输入至少一个整数", "保持输入顺序", "输出使用单个空格分隔"],
        starter_code="values = list(map(int, input().split()))\n# 使用清晰的循环或列表推导式完成\n",
        hints=[
            "过滤条件同时包含大于零和能被2整除。",
            "表达式部分计算 value * value。",
            "join 前需要把整数转换为字符串。",
        ],
        tests=tests,
    )


def _safe_parse(*, problem_id: str, seed: int) -> GeneratedProblemBundle:
    rng = random.Random(seed)
    tokens = ["12", "bad", "-5", "3.2", "0", "7"]

    def render(values: list[str]) -> tuple[str, str]:
        parsed: list[int] = []
        for value in values:
            try:
                parsed.append(int(value))
            except ValueError:
                continue
        return f"{len(values)}\n" + "\n".join(values) + "\n", f"{len(parsed)} {sum(parsed)}\n"

    samples = [
        tokens,
        [str(rng.randint(-50, 50)) if index % 3 else "x" for index in range(12)],
        ["x"],
    ]
    tests = tuple(
        _case(f"sp-{index}", "public" if index == 1 else "hidden", *render(values))
        for index, values in enumerate(samples, start=1)
    )
    return _bundle(
        problem_id=problem_id,
        template_id="SAFE-PARSE",
        title="安全整数汇总",
        prompt="读取 n 行文本，仅统计能够被 int 正常转换的整数，输出有效数量和总和。",
        concept_id="PY-EXC-01",
        constraints=["1 ≤ n ≤ 200", "非法文本应被忽略", "只捕获能够处理的转换异常"],
        starter_code="n = int(input())\nvalid = []\n# 使用 try/except 逐行解析\n",
        hints=[
            "把 try 块限制在 int 转换操作。",
            "转换失败时捕获 ValueError 并继续。",
            "最终输出 len(valid) 与 sum(valid)。",
        ],
        tests=tests,
    )
