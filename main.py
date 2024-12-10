import asyncio
import edge_tts
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

OUTPUT_FILE = "/tmp/test.mp3"
app = Flask(__name__)
CORS(app, supports_credentials=True)


async def stream_audio(text, voice, rate="+0%", pitch="+0Hz") -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


def audio_generator(text, voice, rate, pitch):
    loop = asyncio.new_event_loop()
    coroutine = stream_audio(text, voice, rate, pitch)
    while True:
        try:
            chunk = loop.run_until_complete(coroutine.__anext__())
            yield chunk
        except StopAsyncIteration:
            break


def make_response(code, message, data=None):
    response = {
        'code': code,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)


@app.route('/tts', methods=['POST'])
def tts():
    data = request.get_json()
    text = data['text']
    voice = data.get('voice', 'zh-CN-YunxiNeural')
    file_name = data.get('file_name', OUTPUT_FILE)
    rate = data.get('rate', "+0%")  # 默认语速
    pitch = data.get('pitch', "+0Hz")  # 默认音调

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    communicate.save_sync(file_name)
    return send_file(file_name, mimetype='audio/mpeg')


@app.route('/tts/stream', methods=['POST'])
async def stream_audio_route():
    data = request.get_json()
    text = data['text']
    voice = data.get('voice', 'zh-CN-YunxiNeural')
    rate = data.get('rate', "+0%")  # 默认语速
    pitch = data.get('pitch', "+0Hz")  # 默认音调

    return Response((audio_generator(text, voice, rate, pitch)), content_type='application/octet-stream')


@app.route('/voices', methods=['GET'])
async def voices():
    try:
        voices = await edge_tts.list_voices()
        return make_response(200, 'OK', voices)
    except Exception as e:
        return make_response(500, str(e))


if __name__ == "__main__":

    app.run()
