from openai import OpenAI

client = OpenAI()


def run(text: str) -> str:
    return client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=30, max_tokens=256
    ).choices[0].message.content
