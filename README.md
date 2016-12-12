# newTrackon

newTrackon is a service to monitor the status and health of existing open and public trackers that anyone can use.
It also allows to submit new trackers to add them to the list.

newTrackon is based on the abandoned [Trackon](http://repo.cat-v.org/trackon/) by [Uriel †](https://github.com/uriel).

## Installation

After cloning the repo, make sure you have python2.7, pip and sqlite3 installed (default in all major distributions).

To install python dependencies, just run
```
pip install -r requirements.txt
```
This will install requests, bottle, paste and mako.

Then, create the database with
```
sqlite3 trackon.db < trackon.schema
```

Finally, run 
```
python server.py
```
This will start the web server in all interfaces at port 8080, you can access to the main page opening in your browser `localhost:8080`.
You can change the IP and port of the server editing the last line of server.py.

## Contributors

Feel free to make suggestions, create pull requests, report issues or any other feedback.

Contact me on [twitter](https://twitter.com/CorralPeltzer) or on corral.miguelangel@gmail.com
