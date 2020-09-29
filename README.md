RiffShuffle
===========

My 2020 MEng project, advised by Eran Egozy

Don't expect the code to be too good, it was all written under time pressure

## Setup

Versions of things are very not extensively tested.

### setup and data preprocessing (run this once)

- set up and activate a virtualenv with Python 3, probably Python 3.6 at least?
- `pip install -r requirements.txt`
- run `fetch.sh` to hopefully get all the data from the right places; if something fails, read this script and see if you can track the data down???
- run `parse_all.py` to parse everything into our format and store it in pickle. ~~Nottingham is very slow, like a few minutes; the others should be a few seconds each.~~ Everything is fast now because I upgraded my dependencies? ¯\\_(ツ)\_/¯

### server/client

- Server: with the virtualenv active, `python server.py`
- Client: `npm install; npm start` (`yarn` will probably work too (I forgot which dependency manager I've been using in which project, I guess this one was `npm`))

(The computations are simple enough that they could probably be done directly on the client in a WebWorker or something. I did a server/client architecture originally because I wanted to leave the door open to use more advanced machine learning libraries on the backend. That didn't happen, but it's too late now. I mean, I could probably sit down for a few hours to a few days and port all the logic to JavaScript if I felt like it, but...)

### data

See `usertests`. We lost several harmonizations because users selected the wrong melody or uploaded the wrong file: 1-2-3, 2-1-5, 2-4-1 (test number - song number - participant number). Should probably have made the server upload them itself, oops.

We also reordered the songs when presenting them to users in test 2 to get more varied data. The JSON files provided here are in the order used in test 1 and described in the thesis; in the second test, they were presented in the order song1, song4, song2, song3.
