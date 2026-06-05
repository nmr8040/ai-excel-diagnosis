from datetime import datetime, timedelta
from typing import Dict, List, Optional


def create_improvement_actions(ai_report: dict, check_results: Optional[List[dict]] = None) -> List[dict]:
    actions = []
    seen_titles = set()

    for imp in ai_report.get("top_improvements", ai_report.get("improvements", []))[:5]:
        title = imp.get("title", "改善アクション")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        priority = imp.get("priority", "中")
        due_days = {"高": 7, "中": 14, "低": 30}.get(priority, 14)
        actions.append({
            "title": title,
            "description": imp.get("description", ""),
            "priority": priority,
            "owner": "",
            "due_date": (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d"),
            "status": "未着手",
        })

    check_action_map = {
        "空白セル": ("入力ミスが多い列を確認する", "空白セルが多い列の入力ルールを見直し、必須項目化を検討する"),
        "重複行": ("重複データの原因を調査する", "二重登録の原因を特定し、登録前チェックの仕組みを導入する"),
        "偏り": ("特定担当者に業務が集中している原因を確認する", "業務分散のための体制見直しを実施する"),
        "日付欠損": ("期限切れ案件を整理する", "日付未入力の案件を洗い出し、期限管理プロセスを強化する"),
        "マイナス値": ("マイナス値の入力ミスを確認する", "数値入力時のバリデーションルールを追加する"),
        "数値異常値": ("異常値の原因を調査する", "統計的異常値の発生原因を特定し、入力チェックを強化する"),
    }

    if check_results:
        for r in check_results:
            check_type = r.get("check_type", "")
            if check_type in check_action_map:
                title, desc = check_action_map[check_type]
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                severity = r.get("severity", "medium")
                priority = {"high": "高", "medium": "中", "low": "低"}.get(severity, "中")
                due_days = {"高": 7, "中": 14, "低": 30}.get(priority, 14)
                actions.append({
                    "title": title,
                    "description": f"{desc}（{r.get('message', '')}）",
                    "priority": priority,
                    "owner": r.get("target_column", "") or "",
                    "due_date": (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d"),
                    "status": "未着手",
                })

    for action_text in ai_report.get("next_actions", [])[:3]:
        if action_text in seen_titles:
            continue
        seen_titles.add(action_text)
        actions.append({
            "title": action_text,
            "description": action_text,
            "priority": "中",
            "owner": "",
            "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "status": "未着手",
        })

    return actions[:10]
