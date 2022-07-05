import sys
import string
import random
import json
import argparse

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


testData = []

if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    #ap.add_argument('-file', help='input data file (default stdin)')
    ap.add_argument('outfile', nargs='?', type=argparse.FileType('w'), 
                    default=sys.stdout, help='input data file (default stdout)')
    ap.add_argument('-size', default=10, type=int,
                    help='Number of requests to generate')
    ap.add_argument('-verbose', default=False, type=bool,
                    help='additional printouts)')
    a = ap.parse_args()

    for i in range(a.size):
        testData.append({"Type":id_generator(), 'Name':id_generator(16), 'body':id_generator(32)})

    print(json.dumps(testData))


