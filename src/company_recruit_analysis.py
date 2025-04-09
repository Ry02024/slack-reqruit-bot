import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai

class CompanyRecruitAnalysis:
    """
    求人情報のテキストをもとに、1社を選んで企業概要および採用背景（日本社会の背景を踏まえた考察）を
    400文字以内で生成し、Slack に投稿するクラス。
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

この中の求人情報から1社を選び、以下の点について調査してください：
1. 企業概要（事業内容、規模、所在地など）
2. なぜこの会社がデータサイエンス職を障がい者向けに募集しているのか、現在の日本社会の背景（障がい者雇用促進法、DX推進など）と結びつけた考察

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

    def run_analysis_and_post(self, full_text):
        analysis_result = self.analyze_company(full_text)
        caution_text = "※これは本日のウェブサイト情報を Gemini が検索してまとめたものであり、内容の正確性を保証するものではありません。興味のある情報はご自身でご確認ください。"
        final_message = f"{analysis_result}\n\n{caution_text}"
        self.post_message_to_slack(final_message)
