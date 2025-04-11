import os
import json
import requests
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai

class CompanyRecruitAnalysis:
    """
    求人情報のテキスト（1件分）をもとに、対象企業の概要および採用背景（日本の社会状況に基づく考察）を
    400文字以内で生成し、Slack に投稿するクラス。

    また、各求人の分析結果のハッシュを JSON ファイルに保存することで、重複なく1件ずつ分析を実施できるようにします。
    """
    def __init__(self, api_key, slack_bot_token, slack_channel_id):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.chat = self.client.chats.create(
            model='gemini-2.0-flash-exp',
            config={'tools': [{'google_search': {}}]}
        )
        self.slack_bot_token = slack_bot_token
        self.slack_channel_id = slack_channel_id

    def analyze_company(self, full_text):
        prompt = f"""
以下は、障がい者向けのデータサイエンス系求人の要約です：

--- 求人情報 ---
{full_text}
-----------------

この求人情報から対象企業について、以下の点を調査してください：
1. 企業概要（事業内容、規模、所在地など）
2. なぜこの企業がデータサイエンス職を障がい者向けに募集しているのか、現在の日本社会の背景（障がい者雇用促進法、DX推進等）と結び付けた考察

結果は400文字以内で、箇条書きまたは明快な段落でまとめてください。
"""
        result = self.chat.send_message(prompt)
        response_text = "".join(part.text for part in result.candidates[0].content.parts if part.text)
        print("✅ 分析結果:")
        print(response_text)
        return response_text

    def post_message_to_slack(self, message):
        headers = {
            "Authorization": f"Bearer {self.slack_bot_token}",
            "Content-Type": "application/json"
        }
        today_date = datetime.now().strftime("%Y-%m-%d")
        for channel in self.slack_channel_id:
            payload = {
                "channel": channel,
                "text": message,
                "unfurl_links": False,
                "unfurl_media": False,
            }
            response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
            data = response.json()
            if data.get("ok"):
                print(f"✅ {today_date} に Slack へ分析結果を投稿しました！(チャンネル: {channel})")
            else:
                print(f"❌ 投稿に失敗しました: {data.get('error')} (チャンネル: {channel})")
                print("詳細:", data)

    def load_analysis_results(self, analysis_file):
        if os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_analysis_results(self, results, analysis_file):
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def compute_job_hash(self, job_text):
        return hashlib.sha256(job_text.encode("utf-8")).hexdigest()

    def split_jobs(self, req_text):
        # 求人情報は、空行2行で区切られている前提の簡易な分割処理
        jobs = [job.strip() for job in req_text.strip().split("\n\n") if job.strip()]
        return jobs

    def run_analysis_for_one(self, req_file, analysis_file):
        """
        req_file（求人情報ファイル）から求人情報を分割し、未分析の求人のうち
        先頭1件だけを企業分析して Slack に投稿し、結果を analysis_file に保存します。
        """
        if not os.path.exists(req_file):
            print(f"❌ ファイル {req_file} が見つかりません。")
            return

        with open(req_file, "r", encoding="utf-8") as f:
            req_text = f.read()
        jobs = self.split_jobs(req_text)
        if not jobs:
            print("❌ 求人情報が空です。")
            return

        # 分析済み求人結果のロード
        analysis_results = self.load_analysis_results(analysis_file)

        # 未分析の求人を抽出
        unprocessed_jobs = []
        for job in jobs:
            job_hash = self.compute_job_hash(job)
            if job_hash not in analysis_results:
                unprocessed_jobs.append((job_hash, job))

        if not unprocessed_jobs:
            print("すべての求人情報は既に分析済みです。")
            return

        # 先頭の未分析求人のみを処理
        job_hash, job_text = unprocessed_jobs[0]
        analysis_result = self.analyze_company(job_text)
        caution_text = ("※これは本日のウェブサイト情報を Gemini が検索してまとめたものであり、"
                        "内容の正確性を保証するものではありません。興味のある情報はご自身でご確認ください。")
        final_message = f"{analysis_result}\n\n{caution_text}"
        self.post_message_to_slack(final_message)
        print("企業分析結果:\n", final_message)

        # 分析結果をストックに登録
        analysis_results[job_hash] = {
            "analysis": analysis_result,
            "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()
        }
        self.save_analysis_results(analysis_results, analysis_file)
        print("分析結果を保存しました。")
