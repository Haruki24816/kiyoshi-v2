from gtts import gTTS


def generate_voice(message):
    tts = gTTS(message, lang="ja") 
    tts.save("voice.mp3")
