import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai
from src.gemini_slack_poster import GeminiSlackPoster
from src.company_recruit_analysis import CompanyRecruitAnalysis

# 環境変数の取得（GitHub Secrets 等を利用）
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SLACK_CHANNEL_STR = os.environ.get("SLACK_CHANNEL_ID", "C08BRQGQ2VB").strip()
SLACK_CHANNEL_ID = [ch.strip() for ch in SLACK_CHANNEL_STR.split(",") if ch.strip()]

# 求人情報テキストファイル（data フォルダ内）
MESSAGE_FILE = "data/reqruit.txt"

def main():
    # 環境変数チェック
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY が設定されていません。")
        sys.exit(1)
    if not SLACK_BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN が設定されていません。")
        sys.exit(1)
    if not SLACK_CHANNEL_ID:
        print("❌ SLACK_CHANNEL_ID が設定されていません。")
        sys.exit(1)

    # --- GeminiSlackPoster を使った求人情報要約の Slack 投稿 ---
    poster = GeminiSlackPoster(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
    today_date = datetime.now(ZoneInfo('Asia/Tokyo')).strftime("%Y-%m-%d")
    query = f"{today_date}の障碍者枠のデータサイエンス系求人を調査してください。可能であれば5件探してください。文章はですます調でお願いします。"
    poster.post_search_result(query)

    # --- CompanyRecruitAnalysis を用いた企業分析 ---
    if not os.path.exists(MESSAGE_FILE):
        print(f"❌ ファイル {MESSAGE_FILE} が見つかりません。")
        sys.exit(1)
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        recruitment_text = f.read()

    analyzer = CompanyRecruitAnalysis(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
    analyzer.run_analysis_and_post(recruitment_text)

if __name__ == "__main__":
    main()
