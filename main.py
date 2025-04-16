import os
import uuid
import asyncio
import edge_tts
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
import redis
from dotenv import load_dotenv
import tempfile
from pydub import AudioSegment
from io import BytesIO

# 加载环境变量
load_dotenv()

# Redis 客户端（用于 Vercel KV）
redis_client = redis.Redis.from_url(os.getenv("KV_REST_API_URL"), decode_responses=True)

OUTPUT_FILE = "/tmp/test.mp3"
app = Flask(__name__)
CORS(app, supports_credentials=True, max_age=600, allow_headers="*")

def split_text(text, max_length=300):
    import re
    sentence_endings = r'(?<=[。！？；：、.!?;:])'
    sentences = re.split(sentence_endings, text)
    chunks, current = [], ''
    for sentence in sentences:
        if len(current) + len(sentence) <= max_length:
            current += sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks

def make_response(code, message, data=None):
    response = {'code': code, 'message': message}
    if data is not None:
        response['data'] = data
    return jsonify(response), code, {'Content-Type': 'application/json'}

def get_request_data():
    return request.get_json() if request.method == 'POST' else request.args

@app.route('/tts/store', methods=['POST'])
def store_text():
    data = request.get_json()
    text = data.get('text')
    if not text:
        return make_response(400, 'Text parameter is required')
    text_id = str(uuid.uuid4())
    try:
        redis_client.setex(f"text:{text_id}", 600, text)
        return make_response(200, 'OK', {'text_id': text_id})
    except Exception as e:
        return make_response(500, f"Error storing text: {str(e)}")

@app.route('/tts/stored_ids', methods=['GET'])
def get_stored_text_ids():
    try:
        keys = redis_client.keys("text:*")
        text_ids = [key.split(":")[1] for key in keys]
        return make_response(200, 'OK', {'text_ids': text_ids})
    except Exception as e:
        return make_response(500, f"Error fetching text IDs: {str(e)}")

def get_text_from_request(data):
    if 'text_id' in data:
        text = redis_client.get(f"text:{data['text_id']}")
        if not text:
            return None, 'Text ID not found or expired'
        return text, None
    elif 'text' in data:
        return data['text'], None
    return None, 'Text or text_id parameter is required'

@app.route('/tts', methods=['GET', 'POST'])
async def tts():
    data = get_request_data()
    text, error = get_text_from_request(data)
    if error:
        return make_response(400, error)

    voice = data.get('voice', 'zh-CN-YunxiNeural')
    rate = data.get('rate', "+0%")
    pitch = data.get('pitch', "+0Hz")
    file_name = data.get('file_name', OUTPUT_FILE)

    try:
        chunks = split_text(text)
        audio_segments = []

        for idx, chunk in enumerate(chunks):
            temp_path = f"/tmp/chunk_{idx}.mp3"
            communicate = edge_tts.Communicate(chunk, voice, rate=rate, pitch=pitch)
            await communicate.save(temp_path)
            segment = AudioSegment.from_file(temp_path, format="mp3")
            audio_segments.append(segment)
            os.remove(temp_path)

        full_audio = sum(audio_segments)
        full_audio.export(file_name, format="mp3")
        return send_file(file_name, mimetype='audio/mpeg')

    except Exception as e:
        return make_response(500, f"Error generating TTS: {str(e)}")

@app.route('/tts/stream', methods=['GET', 'POST'])
def stream_audio_route():
    data = get_request_data()
    text, error = get_text_from_request(data)
    if error:
        return make_response(400, error)

    voice = data.get('voice', 'zh-CN-YunxiNeural')
    rate = data.get('rate', "+0%")
    pitch = data.get('pitch', "+0Hz")

    def sync_stream_generator():
        async def async_gen():
            try:
                for chunk_text in split_text(text):
                    communicate = edge_tts.Communicate(chunk_text, voice, rate=rate, pitch=pitch)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            yield chunk["data"]
            except Exception as e:
                yield f"Error: {str(e)}".encode()

        # 把 async 生成器转成同步数据
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agen = async_gen().__aiter__()
        try:
            while True:
                chunk = loop.run_until_complete(agen.__anext__())
                yield chunk
        except StopAsyncIteration:
            pass
        except Exception as e:
            yield f"Error: {str(e)}".encode()

    return Response(sync_stream_generator(), content_type='application/octet-stream')


@app.route('/voices', methods=['GET', 'POST'])
def voices():
    try:
        voices = asyncio.run(edge_tts.list_voices())
        return make_response(200, 'OK', voices)
    except Exception as e:
        return make_response(500, f"Error fetching voices: {str(e)}")

if __name__ == "__main__":
    app.run()
