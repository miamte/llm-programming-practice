from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('OPEN_API_KEY')

def summarize_txt(file_path: str):
    client = OpenAI(api_key=api_key)

    # 주어진 텍스트 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        txt = f.read()

    # 요약을 위한 시스템 프롬프트 생성
    system_prompt = f'''
    너는 다음 글을 요약하는 봇이다. 아래 글을 읽고, 저자의 문제 인식과 주장을 파악하고, 주요 내용을 요약하라. 

    작성해야 하는 포맷은 다음과 같다. 
    
    # 제목

    ## 저자의 문제 인식 및 주장 (15문장 이내)
    
    ## 저자 소개

    
    =============== 이하 텍스트 ===============

    { txt }
    '''

    print(system_prompt)
    print('=========================================')

    # OpenAI API를 사용한 요약 생성
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
        ]
    )

    return response.choices[0].message.content

if __name__ == '__main__':
    file_path = '/Users/euni/SrcRepo/hsmu/output/opensource_llm_with_preprocessing.txt'
    summary = summarize_txt(file_path)
    print(summary)

    # 요약 내용 파일 저장
    with open('./output/crop_model_summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary)