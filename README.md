# AI Excel 診断システム

Excelファイルをアップロードすると、AIが中身を診断し、ミス・異常値・放置案件・改善ポイントを見つけて改善レポートとして表示するシステムです。

単なるExcel集計ツールではなく、**Excelの中に埋もれている業務改善ポイントを見つける**ことを目的としています。

## 主な機能

- **Excelアップロード** — `.xlsx` / `.xls` / `.csv` に対応
- **データプレビュー** — 先頭50行を画面表示
- **基本チェック** — 空白セル、重複行、異常値、日付欠損、マイナス値、極端値、期間変動、偏り
- **AI診断** — 業務種別推定、リスク分析、改善提案（API未設定時はダミー診断）
- **診断レポート** — 重要指摘TOP5、改善ポイントTOP5、優先度別表示
- **改善アクション管理** — 診断結果からタスクを自動生成・手動追加
- **診断履歴** — 過去の診断結果を一覧・詳細表示
- **エクスポート** — CSV / Excel / PDF 形式でレポート出力

## 技術スタック

- Python 3.12 / FastAPI
- SQLAlchemy + SQLite
- pandas / openpyxl
- Jinja2 テンプレート
- Docker / docker-compose

## 起動方法

### Docker（推奨）

```bash
# ビルド＆起動
docker compose up --build -d

# ログ確認
docker compose logs -f

# 停止
docker compose down
```

ブラウザで http://localhost:8000 を開いてください。

### ローカル起動

```bash
# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# 起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 使い方

1. **Excelアップロード** — 左メニューから「Excelアップロード」を選択し、ファイルをドラッグ＆ドロップ
2. **診断レポート確認** — アップロード完了後、自動で基本チェック→AI診断→改善アクション作成が実行されます
3. **詳細確認** — 診断履歴または詳細画面で、プレビュー・チェック結果・AI診断を確認
4. **改善アクション** — 自動生成されたアクションのステータスを更新、または手動で追加
5. **エクスポート** — CSV / Excel / PDF でレポートをダウンロード

### サンプルデータ

`sample_data/問い合わせ管理表.csv` をアップロードして動作確認できます。

## AI APIの設定

デフォルトではダミー診断（ルールベース）が動作します。OpenAI APIを使う場合：

```bash
# .env ファイルを作成
cp .env.example .env

# 以下を設定
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

AI診断処理は `app/services/ai_analyzer.py` に分離されており、後からローカルLLM等に差し替えやすい構成です。

## 画面構成

| 画面 | パス | 説明 |
|------|------|------|
| ダッシュボード | `/` | 統計情報・最近の診断・改善アクション |
| Excelアップロード | `/upload` | ファイルアップロード |
| 診断履歴 | `/history` | 過去の診断一覧 |
| 改善アクション | `/actions` | タスク管理 |
| エクスポート | `/export` | レポートダウンロード |
| 設定 | `/settings` | AI設定・システム情報 |
| 診断レポート | `/report/{id}` | 診断結果サマリー |
| 詳細画面 | `/detail/{id}` | 全情報の詳細表示 |

## DB設計

- `excel_uploads` — アップロードファイル情報
- `excel_check_results` — 基本チェック結果
- `excel_ai_reports` — AI診断レポート（JSON）
- `improvement_actions` — 改善アクション

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/upload` | ファイルアップロード＆診断実行 |
| GET | `/api/uploads` | アップロード一覧 |
| POST | `/api/actions` | 改善アクション作成 |
| PUT | `/api/actions/{id}` | 改善アクション更新 |
| GET | `/api/export/{id}/{format}` | レポートエクスポート（csv/excel/pdf） |

## プロジェクト構成

```
├── app/
│   ├── main.py              # FastAPIアプリ
│   ├── config.py            # 設定
│   ├── database.py          # DB接続
│   ├── models.py            # SQLAlchemyモデル
│   ├── routers/
│   │   ├── pages.py         # 画面ルート
│   │   └── api.py           # APIルート
│   ├── services/
│   │   ├── excel_reader.py  # Excel読み取り
│   │   ├── basic_checker.py # 基本チェック
│   │   ├── ai_analyzer.py   # AI診断（差し替え可能）
│   │   ├── action_creator.py# 改善アクション生成
│   │   ├── diagnosis_service.py # 診断オーケストレーション
│   │   └── export_service.py# エクスポート
│   ├── templates/           # HTMLテンプレート
│   └── static/              # CSS
├── data/
│   ├── uploads/             # アップロードファイル
│   └── db/                  # SQLiteデータベース
├── sample_data/             # サンプルCSV
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## ライセンス

MIT
