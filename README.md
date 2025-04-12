# Slack求人分析ボット

このプロジェクトは、求人情報テキストを解析し、その結果を Slack に投稿する自動化システムです。Gemini API を利用して求人情報の要約および、各企業の概要・募集背景（特に障がい者向けデータサイエンス系求人）を抽出・生成します。また、同一企業については重複分析を防ぐ仕組みを備えており、分析結果は JSON ファイルに保存されます。

---

## プロジェクト構成

リポジトリのディレクトリ構造は以下のとおりです。

```
SlackRecruitBot/
├── .github
│   └── workflows
│       ├── summary.yml           # 毎日9時に求人要約を生成し Slack に投稿するワークフロー
│       └── analysis.yml          # 毎日10時～14時に1時間ごとに1件ずつ企業分析を実行し Slack に投稿するワークフロー
├── data
│   ├── reqruit.txt               # 求人情報が記載されたテキストファイル（入力データ）
│   └── analysis_results.json     # 各企業の分析結果を保存する JSON ファイル（重複を防ぐキーとして会社名を使用）
├── src
│   ├── __init__.py               # パッケージ初期化用の空ファイル
│   ├── gemini_slack_poster.py    # GeminiSlackPoster クラス：求人情報の要約を生成し、Slack に投稿する
│   ├── company_recruit_analysis.py  # CompanyRecruitAnalysis クラス：求人情報から企業分析を実施し、重複チェック後に Slack に投稿する
│   └── main.py                   # エントリーポイント。コマンドライン引数により求人要約（summary）か企業分析（analysis）を実行
├── requirements.txt              # プロジェクトで必要な Python パッケージ一覧
└── README.md                     # 本ドキュメント
```

---

## コンポーネント概要

### GeminiSlackPoster クラス

- **役割:**  
  求人情報の要約を Gemini API を用いて生成し、その結果を Slack に投稿します。  
  要約結果は `data/reqruit.txt` にも保存されるため、後から内容を確認できます。

- **主な機能:**  
  - Gemini API への問い合わせによる求人情報の要約生成  
  - 要約に関する参照情報（grounding metadata）の抽出  
  - Slack API を利用したメッセージ投稿

### CompanyRecruitAnalysis クラス

- **役割:**  
  求人情報ファイル（`data/reqruit.txt`）に記載された求人案件の中から、未分析の企業について、企業概要や募集背景を Gemini API で分析し、その結果を Slack に投稿します。  
  同一の会社は重複して分析されないよう、抽出した会社名をキーとして JSON ファイル（`data/analysis_results.json`）に保存します。

- **主な機能:**  
  - 求人情報テキストの分割と各案件の会社名の抽出  
  - 既存の分析結果との重複チェック  
  - Gemini API を用いた企業分析結果の生成  
  - 分析結果の Slack 投稿と JSON への保存

### main.py（エントリーポイント）

- **役割:**  
  コマンドライン引数に応じて求人要約（`--mode summary`）または企業分析（`--mode analysis`）を実行します。  
  CI/CD のワークフローからは、この main.py を実行することで各処理が定刻に動作します。

---

## 使用データ

- **data/reqruit.txt:**  
  求人情報が5件分記載されています。  
  ※ 各求人は、例えば「番号. 会社名 - 職種」の形式になっている必要があります。

- **data/analysis_results.json:**  
  既に分析された企業の結果が、会社名をキーとして JSON 形式で保存されます。  
  これにより、同一の企業が重複して分析されるのを防ぎます。

---

## インストール方法

1. リポジトリをクローンします。
   ```bash
   git clone https://github.com/your_username/SlackRecruitBot.git
   cd SlackRecruitBot
   ```

2. 仮想環境を作成し、有効化します。
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
   ```

3. 必要なパッケージをインストールします。
   ```bash
   pip install -r requirements.txt
   ```

---

## 実行方法

### ローカル実行

- 求人情報の要約結果を生成する場合（summary モード）：
  ```bash
  python -m src.main --mode summary
  ```

- 未分析の求人に対して企業分析を実施する場合（analysis モード）：
  ```bash
  python -m src.main --mode analysis
  ```

### GitHub Actions による定刻実行

- **summary.yml:**  
  毎日9時（UTC 0:00）に求人要約が実行され、`data/summary_result.txt` に保存および Slack 投稿されます。

- **analysis.yml:**  
  毎日10時～14時（UTC 1:00～5:00）に、`--mode analysis` で未分析求人の企業分析が1件ずつ実施され、Slack に投稿されます。

※ 各ワークフローでは、環境変数（GEMINI_API_KEY、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）を GitHub Secrets で管理してください。

---

## CI/CD 設定

GitHub Actions のワークフローは、`.github/workflows/` ディレクトリに配置します。たとえば、求人要約用の `summary.yml` と企業分析用の `analysis.yml` をそれぞれ設定してください。  
また、自動コミット＆プッシュを行いたい場合は、EndBug/add-and-commit アクションを利用して、生成結果ファイル（例：data/summary_result.txt や data/analysis_results.json）を自動コミットするように設定できます。

---

## License

このプロジェクトは MIT ライセンスのもとで公開されています。
