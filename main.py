import json
import openai
import tiktoken
import gradio as gr
from gtts import gTTS
from collections import deque
import threading
import pygame
import io

DEBUG = False
index = None


class Conversation:
    def __init__(self, limit=5, debug=False) -> None:
        self.debug = debug
        self.system_message = ""
        self.messages = deque(maxlen=limit)

    def prepare_prompt(self, prompt):
        '''Get the user input and append it to prompt body. Return the prompt body.'''
        self.messages.append({"role": "user", "content": prompt})
        return [{"role": "system", "content": self.system_message}] + list(self.messages)

    def append_response(self, response):
        '''Get the assistant response and append it to prompt body.'''
        self.messages.append({"role": "assistant", "content": response})

    def set_system_message(self, system_message):
        self.system_message = system_message

    def __len__(self):
        return num_tokens_from_messages(self.messages)

    def __repr__(self) -> str:
        return json.dumps(self.messages, indent=4, ensure_ascii=False)

    def __str__(self) -> str:
        return json.dumps(self.messages, indent=4, ensure_ascii=False)


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            # every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")


def generate_conversation(prompt, openai_api_key):
    """
    Requests a completion from the OpenAI Text-DaVinci-002 model and returns the completion as a string.
    Parameters:
    - prompt (list): A list of messages for sending api request to OpenAI gpt-3.5-turbo.
    Returns:
    - completion (str): The completion generated by the model.
    """
    openai.api_key = openai_api_key
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=prompt,
    )
    return completions['choices'][0]['message']['content']


def play_sound(audio_buffer):
    # initialize pygame mixer for playing audio
    pygame.mixer.init()
    # load the audio data from the buffer into a pygame Sound object
    sound = pygame.mixer.Sound(audio_buffer)
    # play the audio
    sound.play()
    # wait for the audio to finish playing
    pygame.time.wait(int(sound.get_length() * 1000))
    # cleanup pygame mixer
    pygame.mixer.quit()


def chat(chat_history, system_message, openai_api_key, user_input):
    if openai_api_key == "" and not DEBUG:
        raise gr.Error("OpenAI API Key is required!")
    elif user_input == "":
        raise gr.Error("Please enter a message!")

    conversation.set_system_message(system_message)
    prompt = conversation.prepare_prompt(user_input)
    if DEBUG:
        response = "測試"
    else:
        response = generate_conversation(prompt, openai_api_key)

    tts = gTTS(text=response, lang='zh-TW')
    # create a buffer to hold the audio data
    audio_buffer = io.BytesIO()

    # use the save method to save the audio data to the buffer
    tts.write_to_fp(audio_buffer)

    # rewind the buffer to the beginning
    audio_buffer.seek(0)

    # Create and start a new thread to play the sound
    play_sound_thread = threading.Thread(target=play_sound, args=(audio_buffer,))
    play_sound_thread.start()

    conversation.append_response(response)

    return chat_history + [(user_input, response)]


conversation = Conversation(limit=5)

if __name__ == "__main__":
    pygame.mixer.init()

    with gr.Blocks() as demo:
        gr.Markdown('Voice ChatGPT')

        with gr.Tab("System message"):
            system_message = gr.Textbox(
                "你是一個樂於助人的聊天機器人，你只能用繁體中文回覆人類，一步一步思考並將你提供的解法以詳細且好理解的方式回答人類。", label="ChatGPT System Message", placeholder="機器人行為描述")
            openai_api_key = gr.Textbox(
                label="OpenAI API Key", placeholder="請輸入OpenAI API Key")

        with gr.Tab("ChatGPT"):
            chatbot = gr.Chatbot(label="ChatGPT")
            message = gr.Textbox(placeholder="請輸入訊息")
            message.submit(chat, [chatbot, system_message,
                           openai_api_key, message], chatbot)

    demo.queue().launch(debug=True)
