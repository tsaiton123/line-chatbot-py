from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI
import os
from search import google_search , should_search

app = Flask(__name__)

# LINE API setup
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

# OpenAI API setup
API_KEY = os.environ['OPENAI_API_KEY']
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
SEARCH_ENGINE_ID = os.environ['SEARCH_ENGINE_ID']


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
    user_id = event.source.user_id
    
    try:
        client = OpenAI(
            # This is the default and can be omitted
            api_key=API_KEY,
        )
        # Check if the query requires an online search
        decision = should_search(user_message, client)

        if 'yes' not in decision:
            response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                # {"role": "system", "content": "You are a helpful assistant that provides information."},
                {"role": "user", "content": user_message}
            ]
            )
            ai_message = response.choices[0].message.content

        else:
        
            # Search Google for the user's query
            search_results = google_search(user_message, GOOGLE_API_KEY, SEARCH_ENGINE_ID)
            # Extract relevant data (title, link, snippet) from the search results
            formatted_results = ""
            for item in search_results.get('items', []):
                title = item['title']
                link = item['link']
                snippet = item['snippet']
                formatted_results += f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n\n"

            # Feed the formatted results into the GPT model
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes search results."},
                    {"role": "user", "content": f"Here are the Google search results for the query '{user_message}':\n\n{formatted_results}"},
                    {"role": "user", "content": "Can you summarize these search results for me?"}
                ]
            )
            ai_message = response.choices[0].message.content

    except Exception as e:
        app.logger.error(f"OpenAI API request failed: {e}")
        ai_message = f"Sorry, I couldn't process your request{user_id}."

    # Send AI-generated message back to user
    message = TextSendMessage(text=ai_message)
    line_bot_api.reply_message(event.reply_token, message)
    # line_bot_api.push_message(user_id, message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
