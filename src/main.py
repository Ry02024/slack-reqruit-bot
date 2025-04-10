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
REQ_FILE = "data/reqruit.txt"              # 求人情報の入力ファイル（5件分の求人が記載）
ANALYSIS_RESULTS_FILE = "data/analysis_results.json"  # 分析結果のストック（重複防止用）

def load_analysis_results():
    """分析済み求人結果のファイルを読み込み"""
    if os.path.exists(ANALYSIS_RESULTS_FILE):
        with open(ANALYSIS_RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_analysis_results(results):
    """分析済み求人結果をファイルに保存"""
    with open(ANALYSIS_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def compute_job_hash(job_text):
    """求人情報のテキストからSHA-256のハッシュ値を計算（重複チェック用）"""
    return hashlib.sha256(job_text.encode("utf-8")).hexdigest()

def split_jobs(req_text):
    """
    求人情報のテキストを分割する。
    ここでは、求人情報が空行2行で区切られている前提の簡易実装例です。
    """
    jobs = [job.strip() for job in req_text.strip().split("\n\n") if job.strip()]
    return jobs

def main():
    parser = argparse.ArgumentParser(description="Recruitment Analysis System")
    parser.add_argument("--mode", choices=["summary", "analysis"], required=True,
                        help="実行モード。summary: 5件分の求人要約投稿、analysis: 未分析求人のうち先頭1件の企業分析投稿")
    args = parser.parse_args()

    # 環境変数の取得（GitHub Secrets などから設定される）
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    # SLACK_CHANNEL_ID はカンマ区切りの文字列（例："C08BRQGQ2VB"）をリストに変換
    SLACK_CHANNEL_STR = os.environ.get("SLACK_CHANNEL_ID", "C08BRQGQ2VB").strip()
    SLACK_CHANNEL_ID = ["C08BRQGQ2VB"]

    # 環境変数が正しく設定されているかチェック
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY が設定されていません。")
        sys.exit(1)
    if not SLACK_BOT_TOKEN:
        print("❌ SLACK_BOT_TOKEN が設定されていません。")
        sys.exit(1)
    if not SLACK_CHANNEL_ID:
        print("❌ SLACK_CHANNEL_ID が設定されていません。")
        sys.exit(1)

    if args.mode == "summary":
        # 求人要約結果の投稿（全5件分を GemniSlackPoster で取得して Slack 投稿）
        poster = GeminiSlackPoster(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
        today_date = datetime.now(ZoneInfo('Asia/Tokyo')).strftime("%Y-%m-%d")
        query = f"{today_date}の障碍者枠のデータサイエンス系求人を調査してください。可能であれば5件探してください。文章はですます調でお願いします。"
        poster.post_search_result(query)
    elif args.mode == "analysis":
        # 企業分析処理：求人情報ファイル（REQ_FILE）から5件分の求人情報を分割し、
        # 未分析の求人（data/analysis_results.json に記録がない求人）のうち先頭1件を抽出して分析
        if not os.path.exists(REQ_FILE):
            print(f"❌ ファイル {REQ_FILE} が見つかりません。")
            sys.exit(1)
        with open(REQ_FILE, "r", encoding="utf-8") as f:
            req_text = f.read()
        jobs = split_jobs(req_text)
        if not jobs:
            print("❌ 求人情報が空です。")
            sys.exit(1)

        analysis_results = load_analysis_results()
        unprocessed_jobs = []
        for job in jobs:
            job_hash = compute_job_hash(job)
            if job_hash not in analysis_results:
                unprocessed_jobs.append((job_hash, job))
        if not unprocessed_jobs:
            print("すべての求人情報は既に分析済みです。")
            sys.exit(0)

        # 先頭の未分析求人のみ処理する（定刻実行で1件ずつ投稿される前提）
        job_hash, job_text = unprocessed_jobs[0]

        analyzer = CompanyRecruitAnalysis(GEMINI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)
        analysis_result = analyzer.analyze_company(job_text)
        caution_text = "※これは本日のウェブサイト情報を Gemini が検索してまとめたものであり、内容の正確性を保証するものではありません。興味のある情報はご自身でご確認ください。"
        final_message = f"{analysis_result}\n\n{caution_text}"
        analyzer.post_message_to_slack(final_message)

        # 分析結果を保存して重複処理を防止
        analysis_results[job_hash] = {
            "analysis": analysis_result,
            "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()
        }
        save_analysis_results(analysis_results)
    else:
        print("❌ 不正なモードです。")
        sys.exit(1)

if __name__ == "__main__":
    main()
