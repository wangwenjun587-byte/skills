#!/usr/bin/env python3
"""
Skill Test Runner - 自动化测试框架
用于评估本地 Skill 的质量、稳定性和可靠性

支持的测试维度：
  1. 输出质量 (output_quality)    - 输出是否符合预期格式与内容完整性
  2. 稳定性   (stability)         - 多次运行结果是否一致
  3. 幻觉检测 (hallucination)     - 是否返回可验证的准确事实
  4. Prompt遵循 (prompt_follow)   - 是否严格遵守指令约束
  5. Tool调用  (tool_call)        - 工具选择和参数是否正确
  6. 上下文记忆 (context_memory)  - 跨轮次是否正确记住先前信息
  7. 异常处理  (error_handling)   - 面对边界输入是否优雅降级
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── 测试用例数据结构 ────────────────────────────────────────────────────────

DIMENSIONS = {
    "output_quality":   "输出质量",
    "stability":        "稳定性",
    "hallucination":    "幻觉检测",
    "prompt_follow":    "Prompt 遵循",
    "tool_call":        "Tool 调用",
    "context_memory":   "上下文记忆",
    "error_handling":   "异常处理",
}

SCORE_LABELS = {5: "优秀", 4: "良好", 3: "一般", 2: "较差", 1: "失败"}

# ─── 评分辅助 ────────────────────────────────────────────────────────────────

def score_to_emoji(score: int) -> str:
    """将 1-5 分转换为直观 emoji"""
    return {5: "🟢", 4: "🔵", 3: "🟡", 2: "🟠", 1: "🔴"}.get(score, "⚪")

def score_to_label(score: int) -> str:
    return SCORE_LABELS.get(score, "未知")

# ─── 测试维度描述生成 ─────────────────────────────────────────────────────────

def get_dimension_checklist(dimension: str) -> list[str]:
    """返回每个测试维度的检查清单"""
    checklists = {
        "output_quality": [
            "输出格式是否符合 Skill 承诺的格式（Markdown/JSON/表格等）",
            "内容是否完整，没有被截断或省略关键部分",
            "语言风格是否与场景匹配（正式/友好/技术性）",
            "段落结构是否清晰，信息层次合理",
            "有无明显的语法错误或乱码",
        ],
        "stability": [
            "对同一 Prompt 运行 3 次，核心结论是否一致",
            "关键数字/事实在多次运行中是否相同",
            "输出格式是否在多次运行中保持稳定",
            "是否偶尔会随机跳过某些必要步骤",
        ],
        "hallucination": [
            "返回的事实类信息（日期/版本号/API名称）是否可在官方文档中核实",
            "是否捏造了不存在的库、函数、文件路径",
            "引用的代码或命令是否实际可执行",
            "统计数据或引用来源是否真实存在",
        ],
        "prompt_follow": [
            "是否完整执行了用户的每一条指令，无遗漏",
            "是否严格遵守了格式约束（如'只输出JSON'）",
            "是否遵循了字数/篇幅限制",
            "是否忽略了 Prompt 中的负向约束（'不要做X'）",
            "是否在没有被要求时自行扩展了任务范围",
        ],
        "tool_call": [
            "选择的工具是否是完成任务的最优选择",
            "工具参数是否填写正确，无多余/缺失字段",
            "工具调用序列是否合理（先读后写，先搜后取等）",
            "是否在工具出错时有合理的重试或降级逻辑",
            "是否有不必要的冗余工具调用",
        ],
        "context_memory": [
            "在多轮对话中，是否记住了第一轮提到的约束条件",
            "能否正确引用之前轮次中的变量名、文件名、决策",
            "是否因上下文过长而遗忘了早期的重要信息",
            "在角色扮演/会话任务中，是否保持了角色一致性",
        ],
        "error_handling": [
            "输入空字符串或 null 时是否优雅处理而非崩溃",
            "输入超出范围的值时是否给出明确的错误提示",
            "文件不存在/接口超时时是否有合理降级方案",
            "模糊指令下是否主动要求澄清而非猜测执行",
            "是否明确告知用户哪些操作失败了及原因",
        ],
    }
    return checklists.get(dimension, ["（该维度暂无检查项）"])

# ─── 测试报告生成 ────────────────────────────────────────────────────────────

def generate_report(skill_name: str, results: dict, notes: str = "") -> str:
    """
    根据各维度评分生成完整 Markdown 测试报告
    
    参数：
        skill_name: 被测 Skill 名称
        results: {dimension: {"score": 1-5, "evidence": "...", "issues": ["..."]}}
        notes: 附加备注
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_score = sum(v["score"] for v in results.values())
    max_score = len(results) * 5
    pct = round(total_score / max_score * 100) if max_score > 0 else 0

    # 总体评级
    if pct >= 90:
        overall = "🏆 A+ 可信赖"
    elif pct >= 75:
        overall = "✅ A  良好可用"
    elif pct >= 60:
        overall = "⚠️  B  需要改进"
    elif pct >= 40:
        overall = "🚨 C  风险较高"
    else:
        overall = "❌ D  不可靠"

    lines = [
        f"# Skill 可靠性测试报告",
        f"",
        f"| 字段 | 值 |",
        f"|------|-----|",
        f"| 被测 Skill | `{skill_name}` |",
        f"| 测试时间 | {now} |",
        f"| 综合得分 | {total_score} / {max_score}（{pct}%）|",
        f"| 总体评级 | {overall} |",
        f"",
        f"---",
        f"",
        f"## 各维度评分详情",
        f"",
        f"| 维度 | 得分 | 等级 | 摘要 |",
        f"|------|------|------|------|",
    ]

    for dim, data in results.items():
        score = data["score"]
        label = score_to_label(score)
        emoji = score_to_emoji(score)
        evidence = data.get("evidence", "")
        lines.append(f"| {DIMENSIONS.get(dim, dim)} | {emoji} {score}/5 | {label} | {evidence[:50]}{'…' if len(evidence) > 50 else ''} |")

    lines += ["", "---", "", "## 详细分析"]

    for dim, data in results.items():
        score = data["score"]
        emoji = score_to_emoji(score)
        issues = data.get("issues", [])
        evidence = data.get("evidence", "（无描述）")
        lines += [
            f"",
            f"### {emoji} {DIMENSIONS.get(dim, dim)}（{score}/5 分）",
            f"",
            f"**测试证据：**",
            f"> {evidence}",
            f"",
        ]
        if issues:
            lines.append("**发现问题：**")
            for issue in issues:
                lines.append(f"- ❗ {issue}")
            lines.append("")

    if notes:
        lines += ["---", "", "## 附加备注", "", notes, ""]

    lines += [
        "---",
        "",
        f"*报告由 Skill Test Runner 自动生成 · {now}*",
    ]

    return "\n".join(lines)

# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def print_checklist(dimension: Optional[str] = None):
    """打印检查清单供人工评估使用"""
    dims = [dimension] if dimension else list(DIMENSIONS.keys())
    for dim in dims:
        if dim not in DIMENSIONS:
            print(f"⚠️  未知维度: {dim}，可选：{', '.join(DIMENSIONS.keys())}")
            continue
        print(f"\n## {DIMENSIONS[dim]}（{dim}）检查项：")
        for i, item in enumerate(get_dimension_checklist(dim), 1):
            print(f"  {i}. {item}")

def demo_report():
    """生成一份演示报告，帮助理解输出格式"""
    skill_name = "示例-Skill"
    results = {
        "output_quality":  {"score": 5, "evidence": "输出格式规整，Markdown 表格对齐，内容完整", "issues": []},
        "stability":       {"score": 4, "evidence": "3次运行结论一致，但第2次输出格式略有差异", "issues": ["偶尔省略结尾总结段"]},
        "hallucination":   {"score": 3, "evidence": "代码片段可运行，但引用了一个不存在的API端点", "issues": ["`/api/v2/query` 端点不存在", "版本号 v3.2.1 未在官方文档中找到"]},
        "prompt_follow":   {"score": 5, "evidence": "严格遵循了所有约束，包括字数限制和输出语言", "issues": []},
        "tool_call":       {"score": 4, "evidence": "工具选择合理，参数正确，无冗余调用", "issues": ["一次未必要的重复文件读取"]},
        "context_memory":  {"score": 4, "evidence": "正确记住了第1轮的变量名和约束条件", "issues": ["第4轮后遗忘了初始语言约束"]},
        "error_handling":  {"score": 2, "evidence": "空输入时直接报错，未给用户友好提示", "issues": ["空字符串输入导致 KeyError", "无降级处理逻辑"]},
    }
    report = generate_report(skill_name, results, notes="这是一份演示报告，用于说明输出格式。")
    print(report)

def save_report(skill_name: str, report: str, output_dir: str = "."):
    """将报告保存为 Markdown 文件"""
    safe_name = skill_name.replace("/", "-").replace("\\", "-").replace(" ", "_")
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"skill_test_{safe_name}_{date_str}.md"
    filepath = Path(output_dir) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(report, encoding="utf-8")
    print(f"✅ 报告已保存至: {filepath}")
    return str(filepath)

# ─── 主程序 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Skill Test Runner - Skill 可靠性测试工具",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # checklist 子命令：打印检查清单
    p_check = subparsers.add_parser("checklist", help="打印测试检查清单")
    p_check.add_argument("dimension", nargs="?", help=f"指定维度（可选）：{', '.join(DIMENSIONS.keys())}")

    # demo 子命令：生成演示报告
    subparsers.add_parser("demo", help="生成演示报告查看输出格式")

    # dims 子命令：列出所有维度
    subparsers.add_parser("dims", help="列出所有测试维度")

    args = parser.parse_args()

    if args.command == "checklist":
        print_checklist(args.dimension)
    elif args.command == "demo":
        demo_report()
    elif args.command == "dims":
        print("\n可用测试维度：")
        for k, v in DIMENSIONS.items():
            print(f"  {k:20s} → {v}")
    else:
        parser.print_help()
