from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from openai import OpenAI
import os
from search import google_search , should_search
import sqlite3
from flask import send_file
from image_processing import *

app = Flask(__name__)

# LINE API setup
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

# OpenAI API setup
API_KEY = os.environ['OPENAI_API_KEY']
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
SEARCH_ENGINE_ID = os.environ['SEARCH_ENGINE_ID']

# Connect to your database
DATABASE = 'line_bot_users.db'

def create_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

def save_user_to_db(user_id, username):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Insert user_id and username into the database
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    except Exception as e:
        app.logger.error(f"Failed to insert user: {e}")
    finally:
        conn.close()

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


@app.route('/image/<image_id>', methods=['GET'])
def serve_image(image_id):
    # Path to the image in the /tmp directory
    print(os.listdir('/tmp'))  # Debugging line
    image_path = f"/tmp/{image_id}.jpg"
    
    try:
        print(f"Serving image from: {image_path}")  # Debugging line
        return send_file(image_path, mimetype='image/jpeg')
    except Exception as e:
        app.logger.error(f"Failed to serve image: {e}")
        return "Image not found", 404


@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id  # Get the user's ID when they add the bot
    app.logger.info(f"New follower: {user_id}")

    try:
        # Fetch the user's profile to get their display name (username)
        profile = line_bot_api.get_profile(user_id)
        username = profile.display_name

        # Save user_id and username to the database
        save_user_to_db(user_id, username)

        # Send a welcome message to the user
        welcome_message = TextSendMessage(text=f"Thank you for adding me, {username}!")
        line_bot_api.push_message(user_id, welcome_message)
    
    except Exception as e:
        app.logger.error(f"Error fetching user profile: {e}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id
    user_name = line_bot_api.get_profile(user_id).display_name
    
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
        ai_message = f"Sorry, I couldn't process your request, {user_name}."

    # Send AI-generated message back to user
    message = TextSendMessage(text=ai_message)
    line_bot_api.reply_message(event.reply_token, message)
    # line_bot_api.push_message(user_id, message)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_id = event.message.id

    # Download the image from LINE servers
    message_content = line_bot_api.get_message_content(message_id)
    
    # Save the image to the /tmp directory
    temp_image_path = f"/tmp/{message_id}.jpg"
    with open(temp_image_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    
    # Process the image to extract quadrilaterals
    output_dir = "/tmp"
    transformed_image_paths = transform_papers_to_squares(temp_image_path, output_dir)
    
    # Ensure the URL is HTTPS and construct image URLs
    image_messages = []
    for i, transformed_image_path in enumerate(transformed_image_paths):
        image_url = f"https://{request.host}/image/{message_id}_transformed_{i+1}"
        image_message = ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
        image_messages.append(image_message)

    if image_messages:
        # Use `push_message` instead of `reply_message` to avoid token expiration issues
        line_bot_api.push_message(event.source.user_id, image_messages)
    else:
        # Use `push_message` instead of `reply_message`
        line_bot_api.push_message(event.source.user_id, TextSendMessage(text="No valid documents found in the image."))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
