import webbrowser
import time

f = open("over.txt", "r")

count = 0
for url in f:
    line = url.strip()
    webbrowser.open(line, new=0, autoraise=True)
    count += 1
    if count == 20:
        time.sleep(10)
        count = 0
