import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
from dotenv import load_dotenv


load_dotenv()
DISCORD_TOKEN = os.getenv("BOT_TOKEN")


YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'noplaylist': True,
    'keepvideo': False,
    'outtmpl': '%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320'
    }]
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(YDL_OPTIONS)


intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)


queues = {}


def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]


def download_audio(url):
    try:
        info = ytdl.extract_info(url, download=True)
        if 'formats' in info and len(info['url']) > 0:
            return info
        else:
            print(f"Не верный формат URL: {url}")
            return None
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None


@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send('Вы должны быть в голосовом канале, чтобы использовать эту команду.')


@bot.command(name='play')
async def play(ctx, url):
    queue = get_queue(ctx.guild.id)
    queue.append(url)
    channel = ctx.message.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not ctx.message.author.voice:
        await ctx.send("Вы должны быть в голосовом канале, чтобы использовать эту команду.")
        return
    if not voice_client:
        await channel.connect()
        if len(queue) == 1:
            await play_next(ctx)


async def play_next(ctx):
    queue = get_queue(ctx.guild.id)

    if len(queue) > 0:
        url = queue[0]
        filename = download_audio(url)
        if filename is None:
            queue.pop(0)
            await play_next(ctx)
            return

        voice_client = ctx.guild.voice_client

        def after_playing(error):
            if error:
                print(f"Ошибка.")

            queue.pop(0)
            os.remove(filename['title']+'.mp3')
            bot.loop.create_task(play_next(ctx))

        if voice_client:
            try:
                await ctx.send(f"**Сейчас играет:**: {filename['title']}")
                source = discord.FFmpegPCMAudio(filename['url'], **ffmpeg_options)
                voice_client.play(source, after=after_playing)
            except Exception as e:
                print(f"Ошибка при воспроизведении аудио.", e)
                queue.pop(0)
                os.remove(filename['title']+'.mp3')
                await play_next(ctx)
        else:
            print("Бот не находится в голосовом канале.")


@bot.command(name='skip')
async def skip(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()


@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        queue = get_queue(ctx.guild.id)
        queue.clear()
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send('Бот не находится в голосовом канале.')


@bot.command(name='clear')
async def clear(ctx):
    queue = get_queue(ctx.guild.id)
    queue.clear()
    await ctx.send('Очередь очищена.')


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
