import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai

MESSAGE_FILE = "data/reqruit.txt"  # 求人情報要約結果を書き出すファイル

class GeminiSlackPoster:
    """
    Gemini API を利用して求人情報の要約を生成し、その結果を Slack に投稿するクラス。
    """
    def __init__(self, gemini_api, slack_bot_token, slack_channel_id):
        self.gemini_api = gemini_api
        self.slack_bot_token = slack_bot_token
        self.slack_channel_id = slack_channel_id

        # Gemini クライアントの初期化（API バージョン: v1alpha）
        self.client = genai.Client(api_key=self.gemini_api, http_options={'api_version': 'v1alpha'})
        self.search_client = self.client.chats.create(
            model='gemini-2.0-flash-exp',
            config={'tools': [{'google_search': {}}]}
        )

    def robust_get(self, url, max_retries=3, timeout=20):
        for attempt in range(max_retries):
            try:
                r = requests.get(url, allow_redirects=True, timeout=timeout)
                return r
            except Exception:
                if attempt < max_retries - 1:
                    continue
                else:
                    return None

    def get_final_url(self, redirect_url):
        r = self.robust_get(redirect_url)
        return r.url if r else None

    def summary_client(self, original_text):
        summary_prompt = f"""
        以下の文章を簡潔かつ見やすく整理し、求人情報が一目でわかるように、箇条書きで5件にまとめてください。

        【要件】
        - 最初に「*本日のデータサイエンス系障がい者求人はこちらです：*」と記載してください。
        - それぞれの求人の企業名、勤務地（リモート勤務の可否を含む）、職種、給与、勤務形態、特徴を明記してください。
        - 年齢制限がある場合はそれを記載してください。
        - 各社が採用している障害の種別や割合、具体的な採用人数に関する情報があれば、それも明記してください。
        - 文中の引用番号（[1], [2], [7]など）は可能な限り維持してください。
        - 文章は簡潔で明瞭に。
        - 回答はマークダウン形式（** やその他の記法）ではなく、プレーンテキスト形式で返してください。

        【元のテキスト】
        {original_text}
        """
        summary_response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=summary_prompt
        )
        return summary_response.text.strip()

    def serch_references(self, response):
        if not response.candidates[0].grounding_metadata:
            return "検索結果情報 (grounding_metadata) がありませんでした。"
        grounding_chunks = response.candidates[0].grounding_metadata.grounding_chunks
        if not grounding_chunks:
            return "URLが取得できませんでした。ご自身でも調べてみて下さい。"
        ref_lines = ["*取得した参照サイト一覧:*"]
        for i, chunk in enumerate(grounding_chunks, start=1):
            redirect_url = chunk.web.uri
            final_url = self.get_final_url(redirect_url)
            if final_url is None:
                page_title = "（リダイレクト失敗）"
            else:
                try:
                    resp = self.robust_get(final_url)
                    if resp is None:
                        page_title = "（取得失敗）"
                    elif resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        page_title = soup.title.string if soup.title else "（タイトルなし）"
                    else:
                        page_title = f"（取得できませんでした: {resp.status_code}）"
                except Exception as e:
                    page_title = f"（エラー: {str(e)}）"
            ref_lines.append(f"{i}. <{final_url}|{page_title}>")
        return "\n".join(ref_lines)

    def search_info(self, user_query):
        response = self.search_client.send_message(user_query)
        original_text = ""
        for part in response.candidates[0].content.parts:
            if part.text:
                original_text += part.text + "\n"
        summary_text = self.summary_client(original_text)
        references_text = self.serch_references(response)
        return summary_text, references_text, response

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
                print(f"✅ {today_date} に Slack へメッセージを投稿しました！(チャンネル: {channel})")
            else:
                print(f"❌ Slack への投稿に失敗しました: {data.get('error')} (チャンネル: {channel})")
                print("詳細:", data)

    def post_search_result(self, query):
        summary, _, response = self.search_info(query)
        caution_text = "※これは本日のウェブサイト情報を Gemini が検索してまとめたものであり、内容の正確性を保証するものではありません。"
        slack_message = f"*要約結果:*\n{summary}\n\n{caution_text}"
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write(slack_message)
        print("投稿内容:\n", slack_message)
        self.post_message_to_slack(slack_message)
