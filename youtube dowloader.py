from pytubefix import YouTube
from pytubefix.cli import on_progress

print("youtube dowloader\n")
url = input("enter the url here: ")

if(url != ""):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_highest_resolution()
    ys.download()