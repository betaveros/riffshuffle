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
- run `parse_all.py` to parse everything into our format and store it in pickle. Nottingham is very slow, like a few minutes; the others should be a few seconds each.

### server/client

- Server: with the virtualenv active, `python server.py`
- Client: `yarn install; yarn start` (`npm` will probably work too??)

(The computations are simple enough that they could probably be done directly on the client in a WebWorker or something. I did a server/client architecture originally because I wanted to leave the door open to use more advanced machine learning libraries on the backend. That didn't happen, but it's too late now. I mean, I could probably sit down for a few hours to a few days and port all the logic to JavaScript if I felt like it, but...)

### data

coming at some undetermined point in the future
