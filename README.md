# newTrackon

[![Requirements Status](https://requires.io/github/CorralPeltzer/newTrackon/requirements.svg?branch=master)](https://requires.io/github/CorralPeltzer/newTrackon/requirements/?branch=master)

newTrackon is a service to monitor the status and health of existing open and public trackers that anyone can use.
It also allows to submit new trackers to add them to the list.

newTrackon is based on the abandoned [Trackon](http://repo.cat-v.org/trackon/) by [Uriel †](https://github.com/uriel).

Hosted and tested only with Ubuntu 16.04 LTS.

## Installation
After cloning the repo, to make sure you have `python3`, `pip`, `pipenv` and `sqlite3` installed, run

* Ubuntu-Based / Debian:
```
sudo apt-get install python3-pip sqlite3 python3
sudo pip3 install pipenv
```
Then, browse to the project root folder. To install the pipenv environment and dependencies, and enter the pipenv:
```
pipenv install
pipenv shell
```
This will install requests, Flask, tornado, wsgi-requests-logger, and Flask-Mako.

Then, create the database with
```
sqlite3 trackon.db < trackon.schema
```

Finally, run 
```
python3 server.py
```
This will start the web server in all interfaces at port 8080, you can access to the main page opening in your browser `localhost:8080`.
You can change the IP and port of the server editing the last line of server.py.

## Contributors

Feel free to make suggestions, create pull requests, report issues or any other feedback.

Contact me on [twitter](https://twitter.com/CorralPeltzer) or on corral.miguelangel@gmail.com
