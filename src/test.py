from cgi import parse_qs, FieldStorage
from main import rndpage
import tracker

def main():
    args = FieldStorage()
    tkr = ""
    result = None
    if 'tracker' in args:
        tkr = args['tracker'].value
        (success, result, requrl) = tracker.checktracker(tkr)

    html = """<form method="POST"><input type="text" name="tracker" value="%s" size=128>
    <input type="submit"></form>""" % tkr
    if result:
        html += repr(result)

    rndpage(html)

if __name__ == '__main__':
    main()
