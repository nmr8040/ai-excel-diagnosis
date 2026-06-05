import json
from abc import ABC, abstractmethod

from app.config import AI_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL


class AIAnalyzerBase(ABC):
    @abstractmethod
    def generate_ai_excel_report(self, summary_data: dict) -> dict:
        pass


class DummyAIAnalyzer(AIAnalyzerBase):
    """AI API未設定時のダミー診断。後からOpenAI等に差し替え可能。"""

    BUSINESS_KEYWORDS = {
        "問い合わせ": ["問い合わせ", "問合せ", "inquiry", "受付"],
        "クレーム管理": ["クレーム", "苦情", "complaint"],
        "誤出荷": ["誤出荷", "出荷ミス", "出荷"],
        "請求管理": ["請求", "invoice", "billing"],
        "見積管理": ["見積", "quote", "estimate"],
        "残業管理": ["残業", "overtime", "勤務"],
        "作業日報": ["日報", "作業", "実績"],
        "点検記録": ["点検", "検査", "inspection"],
        "在庫管理": ["在庫", "stock", "inventory"],
        "期限管理": ["期限", "納期", "期日", "deadline"],
    }

    def generate_ai_excel_report(self, summary_data: dict) -> dict:
        columns = summary_data.get("column_names", [])
        check_results = summary_data.get("check_results", [])
        row_count = summary_data.get("row_count", 0)

        business_type = self._detect_business_type(columns)
        important_columns = self._detect_important_columns(columns)
        issues = self._analyze_issues(check_results, columns, row_count)
        risks = self._analyze_risks(check_results, business_type)
        improvements = self._generate_improvements(check_results, business_type, columns)
        priorities = self._assign_priorities(issues, improvements)

        top_issues = sorted(issues, key=lambda x: {"高": 0, "中": 1, "低": 2}[x["priority"]])[:5]
        top_improvements = sorted(improvements, key=lambda x: {"高": 0, "中": 1, "低": 2}[x["priority"]])[:5]

        high_count = sum(1 for i in issues if i["priority"] == "高")
        risk_level = "高" if high_count >= 3 else "中" if high_count >= 1 else "低"

        summary = (
            f"このExcelは「{business_type}」の業務データと推定されます。"
            f"全{row_count}件のデータに対し、{len(check_results)}件の異常・注意点が検出されました。"
            f"特にデータ品質と業務偏りの観点で改善の余地があります。"
        )

        ai_comment = (
            f"経営・管理の観点から見ると、このデータには"
            f"{'重大なリスクが複数' if risk_level == '高' else '改善すべきポイントが'}"
            f"存在します。"
            f"まず優先度「高」の項目から対応することで、"
            f"入力ミスによる判断誤りや放置案件の拡大を防げます。"
        )

        next_actions = [
            "優先度「高」の異常項目を担当者と確認する",
            "データ入力ルール（必須項目・フォーマット）を整備する",
            "定期的なデータ品質チェックの仕組みを導入する",
        ]
        if any(r["check_type"] == "偏り" for r in check_results):
            next_actions.insert(1, "業務が特定担当者に集中している原因を調査する")
        if any(r["check_type"] == "重複行" for r in check_results):
            next_actions.insert(1, "重複データの原因を調査し、二重登録を防止する")

        return {
            "business_type": business_type,
            "important_columns": important_columns,
            "issues": issues,
            "risks": risks,
            "improvements": improvements,
            "priorities": priorities,
            "top_issues": top_issues,
            "top_improvements": top_improvements,
            "risk_level": risk_level,
            "summary": summary,
            "ai_comment": ai_comment,
            "next_actions": next_actions,
            "data_count": row_count,
            "anomaly_count": len(check_results),
        }

    def _detect_business_type(self, columns: list[str]) -> str:
        col_text = " ".join(columns).lower()
        scores = {}
        for biz_type, keywords in self.BUSINESS_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in col_text)
            if score > 0:
                scores[biz_type] = score
        if scores:
            return max(scores, key=scores.get)
        return "汎用業務管理"

    def _detect_important_columns(self, columns: list[str]) -> list[str]:
        important_keywords = ("日", "担当", "金額", "数量", "ステータス", "状態", "期限", "顧客", "案件", "名称")
        important = [c for c in columns if any(kw in str(c) for kw in important_keywords)]
        return important[:8] if important else columns[:5]

    def _analyze_issues(self, check_results: list[dict], columns: list[str], row_count: int) -> list[dict]:
        issues = []
        severity_map = {"high": "高", "medium": "中", "low": "低"}
        for r in check_results[:15]:
            issues.append({
                "title": f"{r['check_type']}: {r.get('target_column') or '全体'}",
                "description": r["message"],
                "priority": severity_map.get(r["severity"], "中"),
            })
        if row_count > 500 and not any(i["title"].startswith("偏り") for i in issues):
            issues.append({
                "title": "大量データの管理負荷",
                "description": f"{row_count}件のデータがあり、手動管理の限界に近づいている可能性があります。",
                "priority": "中",
            })
        return issues

    def _analyze_risks(self, check_results: list[dict], business_type: str) -> list[dict]:
        risks = []
        type_risk = {
            "クレーム管理": "未対応クレームの放置による顧客離反リスク",
            "期限管理": "期限切れ案件の見落としによる損失リスク",
            "請求管理": "請求漏れ・重複請求による売上損失リスク",
            "在庫管理": "在庫数の不正確さによる欠品・過剰在庫リスク",
        }
        if business_type in type_risk:
            risks.append({"title": "業務固有リスク", "description": type_risk[business_type], "level": "高"})

        high_checks = [r for r in check_results if r["severity"] == "high"]
        if len(high_checks) >= 3:
            risks.append({
                "title": "データ品質リスク",
                "description": "複数の重大なデータ異常が検出され、経営判断の信頼性が低下しています。",
                "level": "高",
            })
        bias_checks = [r for r in check_results if r["check_type"] == "偏り"]
        if bias_checks:
            risks.append({
                "title": "業務偏りリスク",
                "description": "特定担当者・カテゴリへの業務集中により、ボトルネックや放置が発生する可能性があります。",
                "level": "中",
            })
        return risks

    def _generate_improvements(self, check_results: list[dict], business_type: str, columns: list[str]) -> list[dict]:
        improvements = []
        check_types = {r["check_type"] for r in check_results}

        if "空白セル" in check_types:
            blank_cols = [r["target_column"] for r in check_results if r["check_type"] == "空白セル" and r["target_column"]]
            improvements.append({
                "title": "必須入力項目の明確化",
                "description": f"空白が多い列（{', '.join(blank_cols[:3])}）を必須項目に設定し、入力漏れを防止する。",
                "priority": "高",
            })
        if "重複行" in check_types:
            improvements.append({
                "title": "重複登録防止の仕組み",
                "description": "登録前に既存データとの照合を行うルールを導入する。",
                "priority": "高",
            })
        if "偏り" in check_types:
            improvements.append({
                "title": "業務分散の見直し",
                "description": "特定担当者への業務集中を解消し、バックアップ体制を整備する。",
                "priority": "高",
            })
        if "日付欠損" in check_types:
            improvements.append({
                "title": "期限管理プロセスの強化",
                "description": "日付未入力の案件を週次でレビューし、放置案件を早期発見する。",
                "priority": "高",
            })
        if "数値異常値" in check_types or "マイナス値" in check_types:
            improvements.append({
                "title": "数値入力バリデーション",
                "description": "異常値・マイナス値を入力時に警告するルールを追加する。",
                "priority": "中",
            })

        improvements.append({
            "title": "定期データ品質レビュー",
            "description": f"{business_type}データを月次でレビューし、異常傾向を早期に把握する。",
            "priority": "中",
        })
        improvements.append({
            "title": "データ入力テンプレートの標準化",
            "description": "列定義・入力例・選択肢を統一したテンプレートを全員に展開する。",
            "priority": "低",
        })
        return improvements

    def _assign_priorities(self, issues: list[dict], improvements: list[dict]) -> dict:
        all_items = issues + improvements
        return {
            "高": [i for i in all_items if i.get("priority") == "高"],
            "中": [i for i in all_items if i.get("priority") == "中"],
            "低": [i for i in all_items if i.get("priority") == "低"],
        }


class OpenAIAnalyzer(AIAnalyzerBase):
    def generate_ai_excel_report(self, summary_data: dict) -> dict:
        import httpx

        prompt = self._build_prompt(summary_data)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": "あなたは中小企業の業務改善コンサルタントです。Excelデータを分析し、JSON形式で診断レポートを返してください。"},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _build_prompt(self, summary_data: dict) -> str:
        return f"""以下のExcelデータを分析し、業務改善の診断レポートをJSON形式で返してください。

列情報: {json.dumps(summary_data.get('columns', []), ensure_ascii=False)}
行数: {summary_data.get('row_count')}
基本チェック結果: {json.dumps(summary_data.get('check_results', [])[:20], ensure_ascii=False)}

以下のJSON形式で返してください:
{{
  "business_type": "推定業務種別",
  "important_columns": ["重要列1", "重要列2"],
  "issues": [{{"title": "...", "description": "...", "priority": "高/中/低"}}],
  "risks": [{{"title": "...", "description": "...", "level": "高/中/低"}}],
  "improvements": [{{"title": "...", "description": "...", "priority": "高/中/低"}}],
  "priorities": {{"高": [], "中": [], "低": []}},
  "top_issues": [],
  "top_improvements": [],
  "risk_level": "高/中/低",
  "summary": "要約",
  "ai_comment": "AIコメント",
  "next_actions": ["アクション1", "アクション2"],
  "data_count": 0,
  "anomaly_count": 0
}}"""


def get_ai_analyzer() -> AIAnalyzerBase:
    if AI_PROVIDER == "openai" and OPENAI_API_KEY:
        return OpenAIAnalyzer()
    return DummyAIAnalyzer()


def generate_ai_excel_report(summary_data: dict) -> dict:
    analyzer = get_ai_analyzer()
    report = analyzer.generate_ai_excel_report(summary_data)
    if "top_issues" not in report or not report["top_issues"]:
        report["top_issues"] = report.get("issues", [])[:5]
    if "top_improvements" not in report or not report["top_improvements"]:
        report["top_improvements"] = report.get("improvements", [])[:5]
    return report
