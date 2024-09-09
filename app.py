from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import openai
import os

app = Flask(__name__)

# LINE API setup
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

# OpenAI API setup
openai.api_key = os.environ['OPENAI_API_KEY']

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
        # Generate response using OpenAI
        response = openai.Completion.create(
            engine="text-davinci-003",  # You can choose different models
            prompt=user_message,
            max_tokens=150  # Adjust as needed
        )
        ai_message = response.choices[0].text.strip()
    except Exception as e:
        app.logger.error(f"OpenAI API request failed: {e}")
        ai_message = "Sorry, I couldn't process your request."

    # Send AI-generated message back to user
    message = TextSendMessage(text=ai_message)
    line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
