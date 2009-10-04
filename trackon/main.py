from cgi import FieldStorage
from trackon import tracker
from trackon.web import renderpage, postredir

""" Trackon """

def main():
     
    new_tracker_error = None
    req = FieldStorage()
    if 'tracker-address' in req:
        trdrs = req['tracker-address'].value.split()
        for t in trdrs:
            new_tracker_error = tracker.incoming(t)
            if new_tracker_error:
                break


        if not new_tracker_error:
            postredir('/incoming-log')
            return

    ts = tracker.allinfo() 
    renderpage('main', trackers=ts, new_tracker_error=new_tracker_error)


if __name__ == '__main__':
    main()
