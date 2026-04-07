#!/usr/bin/env python3
"""AI 味检测工具：扫描文本中的 AI 写作特征并输出报告。"""

import re
import sys
import json
from collections import Counter

# 高优先级 AI 味连接词（每篇各 ≤ 1 次）
HIGH_PRIORITY_CONNECTORS = [
    "此外", "然而", "值得注意的是", "更重要的是", "总而言之",
    "综上所述", "不可否认", "毋庸置疑", "事实上", "毋庸讳言",
    "众所周知", "毋庸赘述", "诚然", "显而易见",
]

# 破折号
DASH_PATTERN = r"——"

# 否定式排比
NEGATIVE_PATTERN = r"不是[^。？\n]{1,30}，不是[^。？\n]{1,30}，而是"

# 三段式
THREE_PART_PATTERN = r"首先[^。]{2,50}其次[^。]{2,50}(?:最后|最终)[^。]{2,50}"

# 万能开头
GENERIC_OPENER = [
    "在当今快速发展的", "随着.*的发展", "在.*的背景下",
    "在这个.*的时代", "让我们", "在当今社会",
]

# 假客观
FAKE_OBJECTIVE = ["客观来说", "客观地讲", "客观来看", "理性来看", "从客观角度"]

# 过度礼貌
OVER_POLITE = ["作为一个AI", "作为一个 AI", "我只是一个语言模型", "希望对您有所帮助"]

# 宣传性用词
PROMOTIONAL = ["深刻地", "意义深远", "不可或缺", "至关重要", "具有重大意义"]

# AI 特有短语
AI_PHRASES = [
    "作为一个人工智能", "我是一个AI", "作为 AI",
    "我不能确定", "我没有个人观点", "我没有感情",
]

# 翻译腔（中国化检测）
TRANSLATION_TONE = [
    "这是一个很好的问题", "感谢你的反馈", "我理解你的感受",
    "从我的角度来看", "在这种情况下", "在一定程度上",
    "不可避免地", "基于此", "与其说", "也就是说",
    "对此", "关于这个问题", "进行了讨论", "取得了进展",
    "具有挑战性",
]


def check_text(text: str) -> dict:
    """扫描文本，返回检测结果。"""
    issues = []
    line_count = len(text.split("\n"))
    char_count = len(text)

    # 1. 破折号
    dashes = re.findall(DASH_PATTERN, text)
    dash_count = len(dashes)
    if dash_count > 2:
        issues.append({"type": "破折号过多", "count": dash_count, "limit": 2, "severity": "high"})
    elif dash_count > 0:
        issues.append({"type": "破折号", "count": dash_count, "limit": 2, "severity": "info"})

    # 2. 高优先级连接词
    for conn in HIGH_PRIORITY_CONNECTORS:
        count = len(re.findall(re.escape(conn), text))
        if count > 1:
            issues.append({"type": f"连接词过多: {conn}", "count": count, "limit": 1, "severity": "high"})
        elif count == 1:
            issues.append({"type": f"连接词: {conn}", "count": 1, "limit": 1, "severity": "info"})

    # 3. 否定式排比
    neg_matches = re.findall(NEGATIVE_PATTERN, text)
    if len(neg_matches) > 1:
        issues.append({"type": "否定式排比过多", "count": len(neg_matches), "limit": 1, "severity": "high"})

    # 4. 三段式
    three_part = re.findall(THREE_PART_PATTERN, text)
    if three_part:
        issues.append({"type": "三段式论证", "count": len(three_part), "severity": "medium"})

    # 5. 万能开头
    for opener in GENERIC_OPENER:
        if re.search(opener, text):
            issues.append({"type": f"万能开头: {opener[:10]}...", "severity": "medium"})

    # 6. 假客观
    for phrase in FAKE_OBJECTIVE:
        if phrase in text:
            issues.append({"type": f"假客观: {phrase}", "severity": "high"})

    # 7. 宣传性用词
    for word in PROMOTIONAL:
        count = text.count(word)
        if count > 0:
            issues.append({"type": f"宣传性用词: {word}", "count": count, "severity": "medium"})

    # 8. 过度礼貌 / AI 身份提醒
    for phrase in OVER_POLITE + AI_PHRASES:
        if phrase in text:
            issues.append({"type": f"AI 身份提醒: {phrase}", "severity": "high"})

    # 9. 翻译腔检测（中国化）
    for phrase in TRANSLATION_TONE:
        if phrase in text:
            issues.append({"type": f"翻译腔: {phrase}", "severity": "medium"})

    # 10. 句子长度分析
    sentences = re.split(r"[。！？\n]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if sentences:
        lengths = [len(s) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        # 计算标准差
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5
        if std_dev < 10:
            issues.append({"type": "句子长度过于均匀", "avg": round(avg_len, 1), "std": round(std_dev, 1), "severity": "medium"})

    # 11. 第一人称检查
    has_i = "我" in text
    if not has_i and char_count > 200:
        issues.append({"type": "缺少第一人称'我'", "severity": "medium"})

    high = sum(1 for i in issues if i["severity"] == "high")
    medium = sum(1 for i in issues if i["severity"] == "medium")
    info = sum(1 for i in issues if i["severity"] == "info")

    return {
        "char_count": char_count,
        "line_count": line_count,
        "total_issues": len(issues),
        "high": high,
        "medium": medium,
        "info": info,
        "issues": issues,
        "score": max(0, 100 - high * 15 - medium * 5),
    }


def print_report(text: str):
    """打印人类可读的报告。"""
    result = check_text(text)
    
    print(f"\n{'='*50}")
    print(f"AI 味检测报告")
    print(f"{'='*50}")
    print(f"字符数: {result['char_count']}  |  行数: {result['line_count']}")
    print(f"人味评分: {result['score']}/100")
    print(f"问题总数: {result['total_issues']} (🔴{result['high']} 🟡{result['medium']} 🟢{result['info']})")
    print(f"{'='*50}")
    
    if not result["issues"]:
        print("✅ 没有检测到明显的 AI 味")
        return
    
    for issue in result["issues"]:
        severity_icon = {"high": "🔴", "medium": "🟡", "info": "🟢"}.get(issue["severity"], "⚪")
        detail = ""
        if "count" in issue:
            detail = f" (出现 {issue['count']} 次，限制 {issue.get('limit', '?')} 次)"
        print(f"  {severity_icon} {issue['type']}{detail}")
    
    print(f"\n{'='*50}")
    if result["score"] >= 80:
        print("整体不错，小修即可")
    elif result["score"] >= 60:
        print("有改进空间，建议重点修复 🔴 问题")
    else:
        print("AI 味较重，建议大幅修改")


if __name__ == "__main__":
    use_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]

    if args:
        with open(args[0], "r", encoding="utf-8") as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("用法: python3 ai_pattern_checker.py <文件路径>")
        print("     echo '文本' | python3 ai_pattern_checker.py")
        print("     python3 ai_pattern_checker.py <文件路径> --json")
        sys.exit(1)

    if use_json:
        print(json.dumps(check_text(text), ensure_ascii=False, indent=2))
    else:
        print_report(text)
