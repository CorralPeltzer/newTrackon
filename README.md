# newTrackon

newTrackon is a service to monitor the status and health of existing open and public trackers that anyone can use. It
also allows to submit new trackers to add them to the list.

newTrackon is based on the abandoned [Trackon](http://repo.cat-v.org/trackon/) by [Uriel †](https://github.com/uriel).

**By default, newTrackon needs IPv4 and IPv6 internet connectivity, and the application won't start without both. Run
with arguments `--ignore-ipv6` or `--ignore-ipv4` to skip this check.**

## Arguments

run.py [--address ADDRESS] [--port PORT] [--ignore-ipv4]
[--ignore-ipv6]

optional arguments:

* `--address ADDRESS`  Address for the flask server
* `--port PORT`        Port for the flask server
* `--ignore-ipv4`      Ignore newTrackon server IPv4 detection
* `--ignore-ipv6`      Ignore newTrackon server IPv6 detection

## Installation

### With Docker

Pull the image and create the container with

```
docker run -d -p 8080:8080 corralpeltzer/newtrackon --address=0.0.0.0
```

You can now access to the main page opening in your browser `http://localhost:8080`.

### With pipenv

After cloning the repo, make sure you have a working Python 3.12 environment and `pipenv`.

Install the pipenv environment and dependencies:

```
pipenv install
pipenv shell
```

This will install requests, Flask, tornado, and Flask-Mako.

Finally, run

```
python3 run.py
```

You can now access to the main page opening in your browser `http://localhost:8080`.

## Related

* [electromagnet](https://github.com/sdmtr/electromagnet), a Chrome extension to automatically add stable trackers to
  magnet links as you browse

## Contributors

Feel free to make suggestions, create pull requests, report issues or any other feedback.

Contact me on [twitter](https://twitter.com/CorralPeltzer) or on corral.miguelangel@gmail.com
