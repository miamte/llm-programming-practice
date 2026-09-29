from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPEN_API_KEY")

client = OpenAI(api_key = api_key)

model = "gpt-4o"
zero_shot_msg = [
    {"role": "system", "content": "너는 유치원생이야. 유치원생처럼 답변해줘."},
    {"role": "user", "content": "오리"}
]

one_shot_msg = [
    {"role": "system", "content": "너는 유치원생이야. 유치원생처럼 답변해줘."},
    {"role": "user", "content": "참새"},
    {"role": "assistant", "content": "짹짹"},
    {"role": "user", "content": "오리"}
]

few_shot_msg = [
    {"role": "system", "content": "너는 유치원생이야. 유치원생처럼 답변해줘."},
    {"role": "user", "content": "참새"},
    {"role": "assistant", "content": "짹짹"},
    {"role": "user", "content": "말"},
    {"role": "assistant", "content": "히이잉"},
        {"role": "user", "content": "개구리"},
    {"role": "assistant", "content": "개굴개굴"},
    {"role": "user", "content": "오리"}
]

zero_response = client.chat.completions.create(
    model=model,
    messages= zero_shot_msg,  
    temperature=0.9,  # Adjust temperature for creativity
)

one_response = client.chat.completions.create(
    model=model,
    messages= one_shot_msg,  
    temperature=0.9,  # Adjust temperature for creativity
)

few_response = client.chat.completions.create(
    model=model,
    messages= few_shot_msg,  
    temperature=0.9,  # Adjust temperature for creativity
)


print(zero_response.choices[0].message.content)
print(one_response.choices[0].message.content)
print(few_response.choices[0].message.content)