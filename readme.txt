HTML & python YouTube Video Downloader

This project allows you to download YouTube videos via the web using frontend (html/css/js) and backend (python).

HOW TO RUN (you need to have programming experience):

1. Install Python 3.6+ (if you don't have it yet):
- Download from: https://python.org

2. Install the necessary libraries (run in the terminal):
pip install flask pytubefix

3. create a folder, add a venv and put the main.py files next to the templates folder

4. run " flask run " in the venv

HOW THE CODE WORKS:

The YouTube Downloader is a local web application (can be taken to servers) that works in three main steps: first,
the user starts the Python server (main.py) that uses the Flask framework to create a web interface; second, when 
accessing the HTML, the user pastes the URL of a YouTube video into the field provided and clicks on "Download 
Video"; third, the system processes the request: the Python backend uses the pytubefix library to validate the URL,
extract metadata from the video (title, duration and resolution), download the video in MP4 in the highest quality 
available and save it in the project's downloads folder. At the same time, the frontend displays a loading indicator and,
at the end of the process, the browser automatically starts downloading the file to the user's computer. 
All processing occurs locally. The essential libraries are Flask for the web server and pytubefix for interacting 
with the YouTube API and downloading videos.