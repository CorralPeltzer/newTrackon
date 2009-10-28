from trackon.tracker import allinfo

def main():
    print "Content-type: text/plain\n"
    d = allinfo()
    for t in d:
        print t

if __name__ == '__main__':
    main()

