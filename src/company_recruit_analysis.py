import os
import json
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai

class CompanyRecruitAnalysis:
    """
    求人情報のテキスト（1件分）をもとに、対象企業の概要および採用背景（日本の社会状況に基づく考察）を
    400文字以内で生成し、Slack に投稿するクラスです。
    同一の会社名での重複分析を防ぐため、抽出した会社名をキーとして結果を保存します。
    """
    def __init__(self, api_key, slack_bot_token, slack_channel_id):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.chat = self.client.chats.create(
            model='gemini-2.0-flash-exp',
            config={'tools': [{'google_search': {}}]}
        )
        self.slack_bot_token = slack_bot_token
        self.slack_channel_id = slack_channel_id

    def extract_company_name(self, job_text):
        """
        求人情報テキストの最初の行から、番号とピリオドを除去し、ハイフンより前の部分を
        会社名として抽出します。
        期待フォーマット例: "5. 日揮パラレルテクノロジーズ株式会社 - データサイエンティスト"
        → 結果: "日揮パラレルテクノロジーズ株式会社"
        """
        # 求人情報の最初の行を取得
        lines = job_text.splitlines()
        if not lines:
            return None
        first_line = lines[0]
        # まず、番号とドット（"5." の部分）を除去する
        parts = first_line.split(".", 1)
        if len(parts) < 2:
            return None
        remaining = parts[1].strip()  # 例: "日揮パラレルテクノロジーズ株式会社 - データサイエンティスト"
        # 次に、ハイフン（-）より前の部分を会社名として取得する
        company = remaining.split("-", 1)[0].strip()
        print(f"✅ 抽出した企業名:{company}")
        return company

    def analyze_company(self, full_text):
        prompt = f"""
    以下は、障がい者向けのデータサイエンス系求人の一件分の要約です：
    
    --- 求人情報 ---
    {full_text}
    -----------------
    
    以下の要件に従って、この求人情報に基づく企業分析結果を生成してください。
    
    【期待する出力フォーマット例】
    --------------------------------------------------
    🏢 企業概要：
        - 事業内容：○○（例：デジタルマーケティング、データ活用サービスなど）
        - 規模：○○（例：従業員数○○名など）
        - 所在地：○○（例：東京都港区…）
        - 設立：○○（例：2004年など）
    ⚖️ 障がい者雇用と社会背景：
        - 法律上の義務：○○（障害者雇用促進法などに基づく）
        - DX推進：○○（企業の取り組みや業界背景など）
        - その他、企業の取り組み：○○
    --------------------------------------------------
    
    結果は400文字以内で、箇条書きまたは明快な段落でまとめてください。
    なお、回答はマークダウン形式（** やその他の記法）ではなく、プレーンテキスト形式で返してください。
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

    def run_analysis_for_one(self, req_text, analysis_file):
        """
        req_text（求人情報全体）を分割し、各求人について抽出した会社名が
        既に analysis_file に保存されている場合は除外し、未分析の求人のうち先頭1件のみを対象として企業分析を実施します。
        分析結果は Slack に投稿するとともに、analysis_file に会社名をキーとして保存します。
        """
        # 求人情報を空行2行で分割（簡易な実装例）
        jobs = [job.strip() for job in req_text.strip().split("\n\n") if job.strip()]
        if not jobs:
            print("❌ 求人情報が空です。")
            return
    
        # 既存の分析結果を JSON ファイルから読み込む（キーはすでに会社名が登録されている）
        analysis_results = {}
        if os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                analysis_results = json.load(f)
    
        unprocessed_job = None
        for job in jobs:
            company_name = self.extract_company_name(job)
            if not company_name:
                print("警告: 会社名が抽出できませんでした。求人をスキップします。")
                continue
            if company_name in analysis_results:
                print(f"既に分析済みの会社 {company_name} をスキップします。")
                continue
            # 未分析の求人が見つかったらその求人を対象とする
            unprocessed_job = (company_name, job)
            break
    
        if not unprocessed_job:
            print("すべての求人情報は既に分析済みです。")
            return
    
        company_name, job_text = unprocessed_job
        analysis_result = self.analyze_company(job_text)
        caution_text = (
            "※これは本日のウェブサイト情報を Gemini が検索してまとめたものであり、"
            "内容の正確性を保証するものではありません。興味のある情報はご自身でご確認ください。"
        )
        final_message = f"{analysis_result}\n\n{caution_text}"
        self.post_message_to_slack(final_message)
    
        # 分析結果を会社名をキーとして保存（ハッシュではなく、抽出された公式な会社名をそのまま使用）
        analysis_results[company_name] = {
            "analysis": analysis_result,
            "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()
        }
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        print("分析結果を保存しました。")
