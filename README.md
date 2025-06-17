readme

# Websockets

 Websockets is a Python library for building WebSocket servers and clients. It provides an easy-to-use API for handling WebSocket connections, messages, and events.

#### in order to run the code you need to run `pip install -r requirements.txt`
#### and then run `python manage.py runserver` to start the server

good to run redis on port 6379
but for development env not needed

after running go to site `http://localhost:8000/chat/ws/` 
a websocket connection will be started and after that you can send messages 
it will return the total count of messages sent 
it will also return the heartbeat protocol per 30 seconds with timestamp
it has a reconnect button which will reconnect the websocket connection 
it will return the same id while reconnection

in order to run the tests you need to run `pytest tests/`
there are total 7 tests 


you can also see all the metrics by goint to the site `http://localhost:8000/chat/metrics/`
you can open multiple tabs and open `http://localhost:8000/chat/ws/` in order to open multiple websocket connections

or you can also go to `https://websocketking.com/` and use url `ws://localhost:8000/ws/chat/`
in order to open multiple websocket connections

you can also use `wscat -c ws://localhost:8000/ws/chat/ ` on terminal to test the websocket connection


you can also use `daphne -b 0.0.0.0 -p 8000 mywebsite.asgi:application` to run server

# Docker

in order to run docker you need to run `docker build -t django-channels-app .` 
and then `docker run -p 80:80 --name django-channels-container django-channels-app`
to build the image
