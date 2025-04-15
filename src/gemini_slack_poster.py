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
        以下の文章をもとに、求人情報の各案件を分かりやすく整理し、次のフォーマットで必ず5件にまとめて出力してください。
        回答は必ずプレーンテキスト形式で、マークダウン記法や装飾は一切使用せず、絵文字などを用いた視認性の良い形式で返してください。
    
        ※注意：
        1. 求人掲載サイトや求人エージェントの名称（例: "Indeed", "求人ボックス", "障害者転職エージェント ハッピー", "スグJOB" など）は出力結果に含めず、実際に求人を出している企業の正式名称のみを使用してください。
        2. 各求人案件について、1行目には企業名のみを記載してください。もし1行目にハイフン ("-") が含まれている場合は、ハイフンより前の部分を企業名として、ハイフン以降の情報は「職種」の項目に移して記載してください。
        3. 各求人の重要情報（勤務地、職種、給与、勤務形態、特徴など）が『記載なし』または『情報なし』の場合、その案件は出力結果から除外してください。
    
        【期待する出力フォーマット例求人5件表示】
        --------------------------------------------------
        🏢 本日のデータサイエンス系障がい者求人はこちらです：
        
        1. 🏢 株式会社ブレインパッド
            📍 勤務地: 六本木一丁目駅直結（詳細不明）
            💼 職種: データサイエンティスト（ジュニアレベル）
            💰 給与: 記載なし
            ⏰ 勤務形態: 記載なし
            🔍 特徴: データ分析リーディングカンパニー、年間休日127日、公平な評価制度、障害者雇用実績豊富。データ活用、AIモデル構築担当。
        
        2. 🏢 ピアス株式会社
            📍 勤務地: 東京都中央区 または 大阪府大阪市北区
            💼 職種: データサイエンティスト
            💰 給与: 記載なし
            ⏰ 勤務形態: 記載なし
            🔍 特徴: 化粧品ブランド、通販データ分析、正社員登用制度あり。

…

        5. 🏢 株式会社xxxzzz
            📍 勤務地: aaaa駅直結（詳細不明）
            💼 職種: データサイエンティスト（ジュニアレベル）
            💰 給与: 記載なし
            ⏰ 勤務形態: 記載なし
            🔍 特徴: データ分析リーディングカンパニー、年間休日127日、公平な評価制度、障害者雇用実績豊富。データ活用、AIモデル構築担当。
        --------------------------------------------------
        
        【要件】
        - 最初に「本日のデータサイエンス系障がい者求人はこちらです：」と記載してください。
        - 各求人案件について、企業名、勤務地（リモート勤務の可否を含む）、職種、給与、勤務形態、特徴を必ず明記してください。
        - 年齢制限がある場合はそれを記載してください。
        - 各社が採用している障害の種別や割合、具体的な採用人数に関する情報があれば、それも明記してください。
        - 文中の引用番号（[1], [2], [7] など）は可能な限り維持してください。
        - 出力は必ずプレーンテキスト形式で、マークダウン記法やその他の装飾は使用せず、上記の絵文字を付けたフォーマットに従って返してください。
        - ※求人案件の各項目に十分な情報がある場合のみ出力し、不十分な案件は除外してください。
        
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
        # 追加指示：求人掲載サイト（Indeed、求人ボックス、障害者転職エージェント ハッピー、スグJOB など）の名称は出力結果に含めず、
        # 実際に求人を募集している企業の情報のみを対象に情報を生成するように指示する。
        enhanced_query = (
            f"{user_query}\n"
            "注意：求人掲載サイトの名称は出力結果に含めず、実際に求人を出している企業の正式名称のみを使用してください。\n"
            "出力結果が『複数の企業』となっている場合は、特に勤務地が「大阪府梅田本社オフィス」と示されている企業を代表例として特定し、その企業のみの情報を出力してください。\n"
            "各求人案件において、勤務地、職種、給与、勤務形態、特徴などの重要な情報が『記載なし』または『情報なし』となっている案件は、出力結果に含めないでください。"
        )
        response = self.search_client.send_message(enhanced_query)
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
