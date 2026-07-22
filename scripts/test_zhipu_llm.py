import os

from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv()

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    if not api_key:
        raise RuntimeError("LLM_API_KEY is missing in .env")

    if not base_url:
        raise RuntimeError("LLM_BASE_URL is missing in .env")

    if not model:
        raise RuntimeError("LLM_MODEL is missing in .env")

    print("Provider:", os.getenv("LLM_PROVIDER", "unknown"))
    print("Base URL:", base_url)
    print("Model:", model)

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是一个简洁的中文助手。",
            },
            {
                "role": "user",
                "content": "用一句话回复：RiftCoach 的智谱 GLM 接入测试成功。",
            },
        ],
        temperature=0.3,
    )

    print("\n=== Response ===")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()