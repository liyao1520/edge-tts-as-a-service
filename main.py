import asyncio
import edge_tts
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

OUTPUT_FILE = "/tmp/test.mp3"
app = Flask(__name__)
CORS(app, supports_credentials=True)

async def stream_audio(text, voice, rate="+0%", pitch="+0Hz") -> None:
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except Exception as e:
        yield f"Error: {str(e)}".encode()

def audio_generator(text, voice, rate, pitch):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coroutine = stream_audio(text, voice, rate, pitch)
    while True:
        try:
            chunk = loop.run_until_complete(coroutine.__anext__())
            yield chunk
        except StopAsyncIteration:
            break
        except Exception as e:
            yield f"Error: {str(e)}".encode()
            break

def make_response(code, message, data=None):
    response = {
        'code': code,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)

def get_request_data():
    if request.method == 'POST':
        return request.get_json()
    else:
        return request.args

@app.route('/tts', methods=['GET', 'POST'])
def tts():
    data = get_request_data()
    text = data.get('text')
    if not text:
        return make_response(400, 'Text parameter is required')
    
    voice = data.get('voice', 'zh-CN-YunxiNeural')
    file_name = data.get('file_name', OUTPUT_FILE)
    rate = data.get('rate', "+0%")
    pitch = data.get('pitch', "+0Hz")

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        communicate.save_sync(file_name)
        return send_file(file_name, mimetype='audio/mpeg')
    except Exception as e:
        return make_response(500, f"Error generating TTS: {str(e)}")

@app.route('/tts/stream', methods=['GET', 'POST'])
def stream_audio_route():
    data = get_request_data()
    text = data.get('text')
    if not text:
        return make_response(400, 'Text parameter is required')
    
    voice = data.get('voice', 'zh-CN-YunxiNeural')
    rate = data.get('rate', "+0%")
    pitch = data.get('pitch', "+0Hz")

    try:
        return Response((audio_generator(text, voice, rate, pitch)), content_type='application/octet-stream')
    except Exception as e:
        return make_response(500, f"Error streaming TTS: {str(e)}")

@app.route('/voices', methods=['GET', 'POST'])
def voices():
    try:
        voices = asyncio.run(edge_tts.list_voices())
        return make_response(200, 'OK', voices)
    except Exception as e:
        return make_response(500, f"Error fetching voices: {str(e)}")

if __name__ == "__main__":
    app.run()
