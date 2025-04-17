import os
import sys
import json
import hashlib
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from src.gemini_slack_poster import GeminiSlackPoster
from src.company_recruit_analysis import CompanyRecruitAnalysis

# ファイルパスの設定
REQ_FILE = "data/reqruit.txt"             # 入力ファイル（求人情報全体）
ANALYSIS_RESULTS_FILE = "data/analysis_results.json"  # 既存の企業分析結果の保存先
SUMMARY_OUTPUT_FILE = "data/summary_result.txt"       # 求人要約結果の保存先

def main():
    parser = argparse.ArgumentParser(description="Recruitment Analysis System")
    parser.add_argument("--mode", choices=["summary", "analysis"], required=True,
                        help="実行モード。summary: 求人要約投稿、analysis: 重複しない求人のうち先頭の1件を企業分析して Slack に投稿")
    args = parser.parse_args()

    # 環境変数の取得
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    SLACK_CHANNEL_STR = os.environ.get("SLACK_CHANNEL_ID", "C08BRQGQ2VB").strip()
    SLACK_CHANNEL_ID = ["C08BRQGQ2VB", "C08DRKGJ62W"]

    if not GEMINI_API_KEY or not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("❌ 必要な環境変数が設定されていません。")
        sys.exit(1)

    if args.mode == "summary":
        # 求人要約の投稿（GeminiSlackPoster クラスを利用）
        poster = GeminiSlackPoster(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
        today_date = datetime.now(ZoneInfo('Asia/Tokyo')).strftime("%Y-%m-%d")
        query = f"{today_date}の障碍者枠のデータサイエンス系求人を調査してください。可能であれば5件探してください。文章はですます調でお願いします。"
        poster.post_search_result(query)
    elif args.mode == "analysis":
        # 企業分析（未分析の求人について、同一の会社名が重複しないようにする）
        if not os.path.exists(REQ_FILE):
            print(f"❌ ファイル {REQ_FILE} が見つかりません。")
            sys.exit(1)
        with open(REQ_FILE, "r", encoding="utf-8") as f:
            req_text = f.read()

        analyzer = CompanyRecruitAnalysis(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
        analyzer.run_analysis_for_one(req_text, ANALYSIS_RESULTS_FILE)
    else:
        print("❌ 不正なモードです。")
        sys.exit(1)

if __name__ == "__main__":
    main()
