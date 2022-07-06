
                              #=============================
                              #- - - - -{ Imports }- - - - -
                              #=============================



import asyncio
import functools
import itertools
import math
import random
import os
import discord
import youtube_dl
import sys

sys.path.append(os.path.abspath("Playlists/"))
from keep_alive import keep_alive
from async_timeout import timeout
from discord.ext import commands
from discord.utils import get
from discord.ext.commands import CommandNotFound




                              #==========================================
                              #- - - - -{ Vars, Options & Data }- - - - -
                              #==========================================




# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''

global currentVolume
currentVolume = 0.5

allowedCommandChannel = "bot-commands"

class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)



                              #================================================
                              #- - - - -{ Create FFMPEG Audio Source }- - - - -
                              #================================================



  
    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches <{}>'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches <{}>'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch <{}>'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for <{}>'.format(webpage_url))

      
        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{}d'.format(days))
        if hours > 0:
            duration.append('{}h'.format(hours))
        if minutes > 0:
            duration.append('{}m'.format(minutes))
        if seconds > 0:
            duration.append('{}s'.format(seconds))

        return ' '.join(duration)




                              #========================================
                              #- - - - -{ Song & Queue Class }- - - - -
                              #========================================




class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester
    
    def create_embed(self):
        tagString = ""
        if self.source.tags:
            if len(self.source.tags) < 5: 
                for tag in self.source.tags: tagString = tagString + "#" + tag + "   "
            else: tagString = "〈#" + self.source.tags[0] + "〉  〈#" + self.source.tags[1] + "〉  〈#" + self.source.tags[2] + "〉  〈#" + self.source.tags[3] + "〉  〈#" + self.source.tags[4] + "〉"
        
        embed = (discord.Embed(title='➙ {}'.format(self.source.title),
                               description='{}'.format(tagString),
                               color=discord.Color.blue())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Views', value='{0:,}'.format(self.source.views))
                 .add_field(name='Likes', value='{0:,}'.format(self.source.likes))
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='Video-URL', value='[Click]({0.source.url})'.format(self))
                 .set_image(url=self.source.thumbnail))
        embed.set_footer(text="Upload at: " + self.source.upload_date)

        return embed

    def create_wonderful_stringint(self, par):
        intString = str(par)[::-1]
        outPutString = ""
        lenPar = len(intString)
        pointCount = (lenPar - (lenPar % 3)) / 3
        if pointCount % 1 == 0: pointCount -= 1
        for i in range(0, round(pointCount)):
          outPutString = outPutString + intString[0:3] + "."
          intString.replace(intString[0:3], "")
        outPutString = outPutString + intString  
        return (outPutString[::-1])


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:


                              #==================================
                              #- - - - -{ Audio Player }- - - - -
                              #==================================


  
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        global activereplay
        activereplay = False
        while True:
            self.next.clear()
            if not self.loop and not activereplay:
                try:
                    async with timeout(30):  # 30 seconds Timeout
                        self.current = await self.songs.get()
                          
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
            elif self.loop and not activereplay:
                theSource = await YTDLSource.create_source(self._ctx, search=str(self.current.source.url), loop=False)
                theSourceSong = Song(theSource)
                self.current = theSourceSong
                activereplay = True
            else:
                theSource = await YTDLSource.create_source(self._ctx, search=str(self.current.source.url), loop=False)
                theSourceSong = Song(theSource)
                self.current = theSourceSong

                temptitle = '✅   Song replay startet'
                embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
                await self._ctx.send(content="<@" + str(self._ctx.message.author.id) + ">", embed=embed)
              
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            self.voice.source.volume = currentVolume
            if activereplay: activereplay = False
            else: await self.current.source.channel.send(embed=self.current.create_embed())
            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()
    
    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None

    async def replay(self):
      if self.is_playing:
        global activereplay
        activereplay = True
        self.voice.stop()
      
class Music(commands.Cog):



                              #==================================
                              #- - - - -{ COG & Voice }- - - - -
                              #==================================


  
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.create_error_embed(ctx, str(error))




                              #==================================
                              #- - - - -{ All Commands }- - - - -
                              #==================================


      
    #- - -{ Join }- - -
      
    @commands.command(name='join', invoke_without_subcommand=True, aliases=['j'])
    async def _join(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
        destination = ctx.author.voice.channel

        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
          
        if ctx.author.voice.channel.user_limit == len(ctx.author.voice.channel.members): await ctx.author.voice.channel.edit(user_limit = ctx.author.voice.channel.user_limit + 1)

        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()
      
        temptitle = '✅   Joined:  ```{}```'.format(str(destination.name))
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    #- - -{ Leave }- - -
      
    @commands.command(name='leave', aliases=['l'])
    async def _leave(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
        
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.")   
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

        temptitle = '✅   Leaved:  ```{}```'.format(str(ctx.message.author.voice.channel.name))
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    #- - -{ Volume }- - -
      
    @commands.command(name='volume', aliases=['v'])
    async def _volume(self, ctx: commands.Context, *, volume):
        if allowedCommandChannel not in ctx.channel.name: return

        if not ctx.voice_state.is_playing: return await self.create_error_embed(ctx, 'Nothing being played at the moment.')
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.")  
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
        
        if int(volume) < 0 or int(volume) > 100:
            await self.create_error_embed(ctx, 'Volume must be between 0 and 100')
          
        voice = get(bot.voice_clients, guild=ctx.message.guild)
        voice.source.volume = int(volume) / 100
        global currentVolume 
        currentVolume = int(volume) / 100
      
        temptitle = '✅   Volume set to:  ```{}%```'.format(volume)
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    #- - -{ Now }- - -
      
    @commands.command(name='now', aliases=['n'])
    async def _now(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
        if ctx.voice_state.current == None: return await self.create_error_embed(ctx, 'Nothing being played at the moment.')
        await ctx.send(embed=ctx.voice_state.current.create_embed())



    #- - -{ Replay }- - -
      
    @commands.command(name='replay', aliases=['rep'])
    async def _replay(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
      
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
          
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            await ctx.voice_state.replay()



    #- - -{ Pause }- - -
          
    @commands.command(name='pause', aliases=['pa'])
    async def _pause(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
    
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
          
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()

            temptitle = '✅   Song paused'
            embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
            await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)



    #- - -{ Resume }- - -
          
    @commands.command(name='resume', aliases=['r'])
    async def _resume(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return

        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.")  
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
      
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()

            temptitle = '✅   Song resumed'
            embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
            await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)



    #- - -{ Stop }- - -
  
    @commands.command(name='stop', aliases=['st'])
    async def _stop(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
        return
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
          
        ctx.voice_state.songs.clear()
        ctx.voice_state.loop = False
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()

        temptitle = '✅   Stopped Music Bot'
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


        
    #- - -{ Skip }- - -
  
    @commands.command(name='skip', aliases=['s'])
    async def _skip(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return

        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
      
        if not ctx.voice_state.is_playing:
            await self.create_error_embed(ctx, 'Not playing any music right now...')

        ctx.voice_state.skip()
      
        temptitle = '✅   Song skipped'
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


    #- - -{ Queue }- - -
  
    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        if allowedCommandChannel not in ctx.channel.name: return
        if ctx.voice_state.loop: return await self.create_error_embed(ctx, 'Loop has to be denabled for this command.')
        if len(ctx.voice_state.songs) == 0: return await self.create_error_embed(ctx, 'The queue is empty.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n-------------------------------------------------------------------------\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)


        
    #- - -{ Shuffle }- - -
  
    @commands.command(name='shuffle', aliases=['sh'])
    async def _shuffle(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
            
        if ctx.voice_state.loop: return await self.create_error_embed(ctx, 'Loop has to be denabled for this command.')
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
        if len(ctx.voice_state.songs) == 0: await self.create_error_embed(ctx, 'The queue is empty.')

        ctx.voice_state.songs.shuffle()
        temptitle = '✅   Queue shuffled'
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)



    #- - -{ Remove }- - -
  
    @commands.command(name='remove', aliases=['re'])
    async def _remove(self, ctx: commands.Context, index):
        if allowedCommandChannel not in ctx.channel.name: return
            
        if ctx.voice_state.loop: return await self.create_error_embed(ctx, 'Loop has to be denabled for this command.')
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.")  
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
        if len(ctx.voice_state.songs) == 0: await self.create_error_embed(ctx, 'The queue is empty.')
        removedSongTitle = ctx.voice_state.songs[int(index) - 1].source.title
        ctx.voice_state.songs.remove(int(index) - 1)
        temptitle = '✅   Song removed from queue: '
        embed = discord.Embed( title = temptitle, description="➙ " + removedSongTitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    #- - -{ Clear }- - -
  
    @commands.command(name='clear', aliases=['c'])
    async def _clear(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
            
        if ctx.voice_state.loop: return await self.create_error_embed(ctx, 'Loop has to be denabled for this command.')
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.")  
        if ctx.voice_state.voice == None: return await self.create_error_embed(ctx, "The bot is currently not in a voicechannel.") 
        if ctx.author.voice.channel != ctx.voice_state.voice.channel: return await self.create_error_embed(ctx, "The bot is currently not in your voicechannel.")
        if len(ctx.voice_state.songs) == 0: return await self.create_error_embed(ctx, 'The queue is already empty.')
        ctx.voice_state.songs.clear()
        temptitle = '✅   Queue cleared '
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    #- - -{ Loop }- - -
  
    @commands.command(name='loop', aliases=['lo'])
    async def _loop(self, ctx: commands.Context):
        if allowedCommandChannel not in ctx.channel.name: return
          
        if not ctx.voice_state.is_playing: return await self.create_error_embed(ctx, 'Nothing being played at the moment.')

        ctx.voice_state.loop = not ctx.voice_state.loop
        temptitle = '✅   Current song unlooped'
        if ctx.voice_state.loop: temptitle = '✅   Current song looped'
        embed = discord.Embed( title = temptitle, colour = discord.Colour.green())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


        
    #- - -{ Play }- - -
  
    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        if allowedCommandChannel not in ctx.channel.name: return
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await self.create_error_embed(ctx, str(e))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    #- - -{ Play Playlist }- - -

    @commands.command(name='playlist', aliases=['pl'])
    async def _playlist(self, ctx: commands.Context, *, playlistname: str):
        if allowedCommandChannel not in ctx.channel.name: return
        if ctx.author.voice == None: return await self.create_error_embed(ctx, "You have to be in a voicechannel.") 

        try: playlistfile = open("Playlists/" + playlistname + ".txt", "r")
        except: return await self.create_error_embed(ctx, 'This playlist does not exist.')
        playlistlines = playlistfile.readlines()
        playlistfile.close()
      
        async with ctx.typing():
            for ln in playlistlines:
                if "Owner>>>" in ln:
                    if not ctx.voice_state.voice: await ctx.invoke(self._join)
                else:
                    try:
                        source = await YTDLSource.create_source(ctx, ln.split('~')[0], loop=False)
                    except YTDLError as e:
                        await self.create_error_embed(ctx, str(e))
                    else:
                        song = Song(source)
        
                        await ctx.voice_state.songs.put(song)
                        await ctx.send('Enqueued {}'.format(str(source)))



                      
    #- - -{ Playlist Add }- - -
                      
    @commands.command(name='playlistadd', aliases=['pla'])
    async def _playlistadd(self, ctx: commands.Context, *, params: str):
        if allowedCommandChannel not in ctx.channel.name: return

        splittedParams = params.split(" ")
        search = params.replace(splittedParams[0] + " ", "")
        playlistpath = "Playlists/" + splittedParams[0] + ".txt"
      
        if not os.path.exists(playlistpath): return await self.create_error_embed(ctx, 'This playlist does not exist.')

        with open(playlistpath) as f:
            hasPerms = (str(ctx.author.id) in f.readline())
            f.close()
            if not hasPerms: return await self.create_error_embed(ctx, 'You do not have permissions to modify this playlist.')
        
        source = await YTDLSource.create_source(ctx, search, loop=False)
      
        with open(playlistpath, "a") as f:  
            f.write("\n" + str(source.url) + "~" + str(source.title)) 
            f.close()
        temptitle = '✅   Successfully added to your playlist '
        embed = discord.Embed( title = temptitle, description=source.title , colour = discord.Colour.green())   
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)



    
    #- - -{ Playlist Remove }- - -
                      
    @commands.command(name='playlistremove', aliases=['plr'])
    async def _playlistremove(self, ctx: commands.Context, *, params: str):
        if allowedCommandChannel not in ctx.channel.name: return

        splittedParams = params.split(" ")

        if len(splittedParams) == 1: return await self.create_error_embed(ctx, 'You have to enter the playlist and the number from the song.')
        try: intedindex = int(splittedParams[1])
        except: return await self.create_error_embed(ctx, 'You have to enter the number from the song, <' + splittedParams[1] + '> is not a valid number.')
      
        playlistpath = "Playlists/" + splittedParams[0] + ".txt"
      
        if not os.path.exists(playlistpath): return await self.create_error_embed(ctx, 'This playlist does not exist.')
        with open(playlistpath, "r") as f:
            lines = f.readlines()
            f.close()
            if not str(ctx.author.id) in lines[0]: return await self.create_error_embed(ctx, 'You do not have permissions to modify this playlist.')

        if len(lines) - 1 < intedindex or intedindex == 0: return await self.create_error_embed(ctx, 'There is not a song with this index in this playlist.')

        theRemovedLine = ""
        with open(playlistpath, "w") as f:
            a = 0
            for line in lines:
                if not a == intedindex: f.write(line)
                else: theRemovedLine = line
                a += 1

        temptitle = '✅   Successfully removed from your playlist '
        embed = discord.Embed( title = temptitle, description="[" + theRemovedLine.split("~")[1] + "](" + theRemovedLine.split("~")[0] + ")" , colour = discord.Colour.green())   
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)

    #- - -{ Show Playlist }- - -
                      
    @commands.command(name='showplaylist', aliases=['spl'])
    async def _showplaylist(self, ctx: commands.Context, *, playlistname: str):
        if allowedCommandChannel not in ctx.channel.name: return

        paramSplits = playlistname.split(" ")
        playlist = paramSplits[0]
        
        playlistpath = "Playlists/" + playlist + ".txt"
      
        if not os.path.exists(playlistpath): return await self.create_error_embed(ctx, 'This playlist does not exist.')

        f = open(playlistpath, "r")
        frl = f.readlines()
        f.close()
        embed = discord.Embed( title = "➙ " + playlist + " (Playlist)", colour = discord.Colour.blue())
        a = 0
        offset = 0
        if len(paramSplits) > 1: offset = int(paramSplits[1]) - 1
          
        if len(frl) < offset + 2: return await self.create_error_embed(ctx, 'The playlist do not have ' + str(offset + 1) + ' titles.')
          
        for ln in frl:
            if a > offset and a < offset + 25: embed.add_field(name="```"+ str(a) +".``` " + ln.split("~")[1], value="-------------------------------------------------------------------------", inline=False)
            a += 1 

      
        try: await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)
        except Exception as e: return await self.create_error_embed(ctx, 'Your playlist is too long. ' + str(e))


          
    #- - -{ Create Playlist }- - -
                      
    @commands.command(name='createplaylist', aliases=['cpl'])
    async def _createplaylist(self, ctx: commands.Context, *, playlistname: str):
        if allowedCommandChannel not in ctx.channel.name: return

        playlistpath = "Playlists/" + playlistname.replace(" ", "_") + ".txt"
      
        if os.path.exists(playlistpath): return await self.create_error_embed(ctx, 'This playlist already exist.')

        with open(playlistpath, 'w') as f:
            f.write('Owner>>>' + str(ctx.author.id))
            f.close()

        temptitle = '✅   Successfully created playlist '
        embed = discord.Embed( title = temptitle, description=playlistname.replace(" ", "_") , colour = discord.Colour.green())   
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)

    #- - -{ Delete Playlist }- - -
                      
    @commands.command(name='deleteplaylist', aliases=['dpl'])
    async def _deleteplaylist(self, ctx: commands.Context, *, playlistname: str):
        if allowedCommandChannel not in ctx.channel.name: return

        playlistpath = "Playlists/" + playlistname.replace(" ", "_") + ".txt"
      
        if not os.path.exists(playlistpath): return await self.create_error_embed(ctx, 'This playlist does not exist.')
        with open(playlistpath) as f:
            hasPerms = (str(ctx.author.id) in f.readline())
            f.close()
            if not hasPerms: return await self.create_error_embed(ctx, 'You do not have permissions to modify this playlist.')
        os.remove(playlistpath)

        temptitle = '✅   Successfully deleted playlist '
        embed = discord.Embed( title = temptitle, description=playlistname.replace(" ", "_") , colour = discord.Colour.green())   
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)


      
    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

    #- - -{ Extra Functions }- - -
  
    async def create_error_embed(self, ctx, descr):
        temptitle = '❌   Failed:  ```{}```'.format(descr)
        embed = discord.Embed( title = temptitle, colour = discord.Colour.red())          
        await ctx.send(content="<@" + str(ctx.message.author.id) + ">", embed=embed)




                              #=====================================
                              #- - - - -{ Bot & Webserver }- - - - -
                              #=====================================




bot = commands.Bot('m!', description='The Ultimate Music Bot by Möhrchen.')
bot.add_cog(Music(bot))
bot.remove_command('help')

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.playing, name="m!play"))
    print('Logged in as:\n{0.user.name}\n{0.user.id}'.format(bot))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    return
    raise error
  

keep_alive()
bot.run(os.getenv("DISCORD_BOT_SECRET"))