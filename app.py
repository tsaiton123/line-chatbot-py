from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI
import os

app = Flask(__name__)

# LINE API setup
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

# OpenAI API setup
API_KEY = os.environ['OPENAI_API_KEY']

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    
    try:
        client = OpenAI(
            # This is the default and can be omitted
            api_key=API_KEY,
        )
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            model="gpt-4o-mini",
        )
        ai_message = chat_completion.choices[0].message.content

    except Exception as e:
        app.logger.error(f"OpenAI API request failed: {e}")
        ai_message = "Sorry, I couldn't process your request."

    # Send AI-generated message back to user
    message = TextSendMessage(text=ai_message)
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
