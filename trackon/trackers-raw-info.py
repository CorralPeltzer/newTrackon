from trackon import tracker
from trackon.web import renderpage, postredir

def main():
     
    ts = tracker.allinfo() 
    renderpage('trackers-raw-info', trackers=ts)


if __name__ == '__main__':
    main()
