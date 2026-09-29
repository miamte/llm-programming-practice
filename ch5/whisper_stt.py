import os
import torch
import pandas as pd
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline 
from pyannote.audio import Pipeline 
from dotenv import load_dotenv
import os
import librosa

load_dotenv()
api_token = os.getenv('HUGGINGFACEHUB_API_TOKEN')
# os.environ["PATH"] += os.pathsep + r"/opt/homebrew/bin/ffmpeg/bin" # conda 사용 안할 시에만 주석 해제

def autio_preprocess(audio_file_path, sample_rate=16000):
    return librosa.load(audio_file_path, sr=sample_rate)

def whisper_stt(
    audio_file_path: str,      
    output_file_path: str = "./output.csv"
):
    device = "cuda:0" if torch.cuda.is_available() else "mps:0" if torch.backends.mps.is_available() else "cpu"
    torch_dtype = torch.float16 if (torch.cuda.is_available() or torch.backends.mps.is_available()) else torch.float32
    model_id = "openai/whisper-large-v3-turbo"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, dtype=torch_dtype, 
        low_cpu_mem_usage=True, 
        use_safetensors=True
    )

    print(f"device : {device}, dtype : {torch_dtype}")
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        return_timestamps=True,  # 청크별로 타임스탬프를 반환
        chunk_length_s=10,  # 입력 오디오를 10초씩 나누기
        stride_length_s=2,  # 2초씩 겹치도록 청크 나누기
    )

    waveform, sample_rate = autio_preprocess(audio_file_path)
    result = pipe({"raw": waveform, "sampling_rate": sample_rate})
    df = whisper_to_dataframe(result, output_file_path)
 
    return result, df


def whisper_to_dataframe(result, output_file_path):
    start_end_text = []

    for chunk in result["chunks"]:
        start = chunk["timestamp"][0]
        end = chunk["timestamp"][1]
        text = chunk["text"].strip()
        start_end_text.append([start, end, text])
        df = pd.DataFrame(start_end_text, columns=["start", "end", "text"])
        df.to_csv(output_file_path, index=False, sep="|")
    
    return df


def speaker_diarization(
        audio_file_path: str,
        output_rttm_file_path: str,
        output_csv_file_path: str
    ):

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=api_token
    )

    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
    pipeline.to(device)

    waveform, sample_rate = autio_preprocess(audio_file_path)
    diarization_pipeline = pipeline({"waveform": torch.from_numpy(waveform).unsqueeze(0), "sample_rate": sample_rate})

    diarization_data = []

    for segment, speaker_id in diarization_pipeline.speaker_diarization :
        diarization_data.append({
            'start': segment.start,
            'duration': segment.duration,
            'speaker_id': speaker_id
        })

    # dump the diarization output to file using RTTM format
    with open(output_rttm_file_path, "w", encoding='utf-8') as rttm:
       rttm.write(str(diarization_pipeline))

    # pandas dataframe으로 변환
    df_rttm = pd.DataFrame(diarization_data)
    # print(df_rttm.head())
    
    df_rttm["end"] = df_rttm["start"] + df_rttm["duration"]

    # speaker_id를 기반으로 화자별로 구간을 나누기
    df_rttm["number"] = None
    df_rttm.at[0, "number"] = 0
    df_rttm["number"] = (df_rttm["speaker_id"] != df_rttm["speaker_id"].shift()).cumsum() - 1

    df_rttm_grouped = df_rttm.groupby("number").agg(
        start=pd.NamedAgg(column='start', aggfunc='min'),
        end=pd.NamedAgg(column='end', aggfunc='max'),
        speaker_id=pd.NamedAgg(column='speaker_id', aggfunc='first')
    )

    df_rttm_grouped["duration"] = df_rttm_grouped["end"] - df_rttm_grouped["start"]

    df_rttm_grouped.to_csv(
        output_csv_file_path,
        index=False,    # 인덱스는 저장하지 않음
        encoding='utf-8' 
    )
    return df_rttm_grouped


def stt_to_rttm(
        audio_file_path: str,
        stt_output_file_path: str,
        rttm_file_path: str,
        rttm_csv_file_path: str,
        final_output_csv_file_path: str
    ):

    result, df_stt = whisper_stt(
        audio_file_path, 
        stt_output_file_path
    )

    df_rttm = speaker_diarization(
        audio_file_path,
        rttm_file_path,
        rttm_csv_file_path
    )

    # rttm 결과에 stt 결과를 매칭
    df_rttm["text"] = ""

    # 각 stt 구간이 어느 rttm 구간에 속하는지 확인
    for i_stt, row_stt in df_stt.iterrows():
        overlap_dict = {}
        for i_rttm, row_rttm in df_rttm.iterrows():
            overlap = max(0, min(row_stt["end"], row_rttm["end"]) - max(row_stt["start"], row_rttm["start"]))
            overlap_dict[i_rttm] = overlap
        
        max_overlap = max(overlap_dict.values())
        max_overlap_idx = max(overlap_dict, key=overlap_dict.get)

        if max_overlap > 0:
            df_rttm.at[max_overlap_idx, "text"] += row_stt["text"] + "\n"

    df_rttm.to_csv(
        final_output_csv_file_path,
        index=False,    # 인덱스는 저장하지 않음
        sep='|',
        encoding='utf-8'
    )  # ④
    return df_rttm


if __name__ == "__main__":
    audio_file_path = "/Users/euni/SrcRepo/hsmu/llm-programming/ch5/audio/guitar.mp3"       # 원본 오디오 파일
    stt_output_file_path = "./guitar.csv"	# STT 결과 파일
    rttm_file_path = "./guitar.rttm"		# 화자 분리 원본 파일
    rttm_csv_file_path = "./guitar_rttm.csv"	# 화자 분리 CSV 파일
    final_csv_file_path = "./guitar_final.csv" # 최종 결과 파일

    df_rttm = stt_to_rttm(
        audio_file_path,
        stt_output_file_path,
        rttm_file_path,
        rttm_csv_file_path,
        final_csv_file_path
    )