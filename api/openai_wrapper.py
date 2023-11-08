import openai
from config import API_KEY

openai.api_key = API_KEY


def get_chatgpt_response(prompt, model="gpt-3.5-turbo-16k", temperature=0.6, max_tokens=9000, n=1):
    messages = [{"role": "system", "content": "You are a Senior Software architect..."}, {"role": "user", "content": prompt}]

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=n,
        stop=None
    )
    generated_response = response['choices'][0]['message']['content'].strip()
    return generated_response if generated_response else ''
