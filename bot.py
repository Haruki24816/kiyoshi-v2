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
import socket


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
    
    current_guild_id = ctx.guild.id

    text = "**Java版**\n"
    for name in data.keys():
        if data[name]["edition"] == "bedrock":
            continue
        if current_guild_id != int(data[name]["guild_id"]):
            continue
        text += name + "\n"
    
    text += "\n**統合版**\n"
    for name in data.keys():
        if data[name]["edition"] == "java":
            continue
        if current_guild_id != int(data[name]["guild_id"]):
            continue
        text += name + "\n"

    await ctx.send(text)


@bot.command(name="管理用リスト")
async def serverlist_for_manage(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("serverlist")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


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
IPアドレス：{socket.gethostbyname(DOMAIN)}
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


@bot.command(name="オウム")
async def oumu(ctx, text):
    await ctx.send(text)
    await ctx.message.delete()


@bot.command(name="リセット")
async def reset(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("reset")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


@bot.command(name="メンテ")
async def maint(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("maint")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


@bot.command(name="自動停止有効")
async def enable_autostop(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("enable_autostop")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


@bot.command(name="自動停止無効")
async def disable_autostop(ctx):
    await ctx.send("通信中")
    data = await request_sekiguchi("disable_autostop")

    if data == False:
        await ctx.send("通信に失敗しました")
        return

    await ctx.send(f"```{str(data)}```")


@bot.command(name="おわり")
async def owari(ctx):
    if ctx.guild.voice_client is not None:
        ctx.guild.voice_client.play(discord.FFmpegPCMAudio("owari.mp3"))


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
