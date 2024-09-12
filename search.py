import requests

# Function to search Google Custom Search
def google_search(query, api_key, search_engine_id):
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    
def should_search(query, client):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Determine whether the following question requires an online search for up-to-date information or not."},
            {"role": "user", "content": query}
        ]
    )
    
    # Get the decision from GPT
    decision = response.choices[0].message.content
    return decision.lower()