import os
import argparse
import re
import json
import shellinford
import pygtrie
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Search duplicates from the index')
parser.add_argument('suffix', metavar='S', help = 'filename suffix')
parser.add_argument('dir', metavar='D', help='search directory')
parser.add_argument('-t', '--threshold', default=5, type=int, help='threshold')
parser.add_argument('-l', '--limit', default=100, type=int, help='maximal size of a clone')
args = parser.parse_args()

fm = shellinford.FMIndex()
pat = re.compile(args.suffix + '$')

file_list = {}
file_id = 0
for d, subdirs, files in os.walk(args.dir):
    for f in files:
        if pat.search(f):
            print('processing {} ...'.format(os.path.join(d, f)))
            file_list[file_id] = os.path.join(d, f)
            file_id = file_id + 1
            with open(os.path.join(d, f), 'r') as content_file:
                content = content_file.read()
                fm.push_back(content)
fm.build()

clones = {}

def search_clone(content, i, start):
    for j in tqdm(range(start, min(len(content) - i, args.limit))):
        text = ''.join(content[i:i+j])
        if text in clones:
            pass
        docs = fm.search(text)
        c = sum([doc.count[0] for doc in docs])
        if c <= 1:
            break
        clones[tuple(content[i:i+j])] = (c, [doc.doc_id for doc in docs])

for fild_id, f in tqdm(file_list.items()):
    with open(f, 'r') as content_file:
        content = content_file.readlines()
        start = args.threshold
        for i in tqdm(range(len(content) - args.threshold + 1)):
            search_clone(content, i, args.threshold)

def add_subtuples(d, t, v):
    for start in range(len(t)-1):
        d[t[start:]] = v

seen_clones = pygtrie.Trie()
keep_clones = []
for item in sorted(clones.items(), key=lambda x: len(x[0]), reverse=True):
    if (item[0] not in seen_clones and not seen_clones.has_subtrie(item[0])) or all(map(lambda k: seen_clones[k][0] < item[1][0], seen_clones.iterkeys(prefix=item[0]))):
        keep_clones.append(item)
        add_subtuples(seen_clones, item[0], item[1])

for clone in keep_clones:
    print('<<<<<<<<')
    print('count {}'.format(clone[1][0]))
    for file in [file_list[id] for id in clone[1][1]]:
        print('appears in {}'.format(file))
    print(''.join(clone[0]))
    print('>>>>>>>>')
