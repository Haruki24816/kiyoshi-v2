import discord
from discord.ext import commands
import aiohttp
from wakeonlan import send_magic_packet
import os
import time
import traceback
import asyncio
from generate_voice import generate_voice
from keep_alive import keep_alive


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SEKIGUCHI_TOKEN = os.getenv("SEKIGUCHI_TOKEN")
SCHEME = "https://"
DOMAIN = os.getenv("SEKIGUCHI_DOMAIN")
MAC_ADDRESS = os.getenv("SEKIGUCHI_MAC_ADDRESS")
COMMAND_PREFIX = "！"


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents) # 全角感嘆符


@bot.command(name="リスト")
async def serverlist(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("serverlist")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    text = ""

    for name in data.keys():
        text += name + "\n"

    await ctx.send(text)


@bot.command(name="起動")
async def start(ctx, name):
    await ctx.send("通信中")
    serverlist_data = await request_sekiguchi("serverlist")

    if serverlist_data == False:
        await ctx.send("通信に失敗しました")
        return

    if name not in serverlist_data:
        await ctx.send("該当するサーバーがありません")
        return

    num = serverlist_data[name]["num"]
    start_data = await request_sekiguchi(f"start/{num}")

    if start_data["message"] == "not_ready":
        await ctx.send("サーバー起動の準備ができていません")
        return
    
    if start_data["message"] == "value_error":
        await ctx.send("該当するサーバーがありません")
        return

    await ctx.send("起動開始")
    timestamp = time.time()

    while True:
        await asyncio.sleep(5)
        status_data = await request_sekiguchi("status")
        if status_data["status"] == "on":
            break
        if status_data["status"] == "error":
            await ctx.send("起動エラー")
            return
        if 300 < (time.time()-timestamp):
            await ctx.send("タイムアウト")
            return

    edition = status_data["info"]["edition"]
    version = status_data["info"]["version"]

    await ctx.send(f"""
起動しました
エディション：{edition}
バージョン：{version}
アドレス：{DOMAIN}
    """)

    while True:
        await asyncio.sleep(30)
        status_data = await request_sekiguchi("status")
        if status_data["status"] == "off":
            await ctx.send("サーバーが停止しました")
            break
        if status_data["status"] == "error":
            await ctx.send("サーバーエラー")
            break


@bot.command(name="停止")
async def stop(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("stop")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    if data["message"] == "not_running":
        await ctx.send("サーバーが起動していません")
        return

    await ctx.send("停止処理を開始します")


@bot.command(name="状態")
async def status(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("status")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


@bot.command(name="入室")
async def join_vc(ctx):
    await ctx.author.voice.channel.connect()


@bot.command(name="退室")
async def leave_vc(ctx):
    await ctx.voice_client.disconnect()


@bot.command(name="あけおめ")
async def akeome(ctx):
    await ctx.send("あけおめ")


@bot.event
async def on_message(message):
    if message.guild.voice_client is not None and COMMAND_PREFIX not in message.content:
        generate_voice(message.content)
        message.guild.voice_client.play(discord.FFmpegPCMAudio("voice.mp3"))

    await bot.process_commands(message)


async def request_sekiguchi(command):
    send_magic_packet(MAC_ADDRESS, ip_address=DOMAIN, port=9)
    timestamp = time.time()
    url = f"{SCHEME}{DOMAIN}/{command}?token={SEKIGUCHI_TOKEN}"
    print(url)
          
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as request:
                    if request.status == 200:
                        data = await request.json()
                    else:
                        raise Exception("connection error")
        except Exception:
            print(traceback.format_exc())
            if 300 < (time.time()-timestamp):
                return False
            await asyncio.sleep(10)
            continue
        break

    return data


keep_alive()
bot.run(DISCORD_TOKEN)
