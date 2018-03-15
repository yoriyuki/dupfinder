import os
import sys
import argparse
import re
import shellinford
import pygtrie
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Search duplicates from the index')
parser.add_argument('suffix', metavar='S', help = 'filename suffix')
parser.add_argument('dir', metavar='D', help='search directory')
parser.add_argument('-t', '--threshold', default=5, type=int, help='threshold')
parser.add_argument('-o', '--output', default='', help='output file')
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

seen_clones = set()
clone_fragments = pygtrie.Trie()
clones = pygtrie.Trie()

def add_clone(seq, v):
    for item in clones.prefixes(seq):
        if item[1][0] <= v[0]:
            del clones[item[0]]
    clones[seq] = v
    for i in range(1, len(seq)):
        for item in clone_fragments.prefixes(seq[i:]):
            if item[1][0] <= v[0]:
                del clone_fragments[item[0]]
        clone_fragments[seq[i:]] = v

def search_clone(content, i, start):
    for j in tqdm(range(start, len(content) - i)):
        seq = content[i:i+j]
        if seq in seen_clones:
            pass
        seen_clones.add(seq)
        text = ''.join(seq)
        docs = fm.search(text)
        c = sum([doc.count[0] for doc in docs])
        if c <= 1:
            break
        frags = clone_fragments.iteritems(prefix=seq)
        if clone_fragments.has_subtrie(seq) or seq in clone_fragments:
            if all(map(lambda item: item[1][0] < c, frags)):
                add_clone(seq, (c, [doc.doc_id for doc in docs]))
            else:
                break
        else:
            add_clone(seq, (c, [doc.doc_id for doc in docs]))

for fild_id, f in tqdm(file_list.items()):
    with open(f, 'r') as content_file:
        content = tuple(content_file.readlines())
        start = args.threshold
        for i in tqdm(range(len(content) - args.threshold + 1)):
            search_clone(content, i, args.threshold)

if args.output == '':
    output = sys.stdout
else:
    output = open(args.output, 'w')

for clone in sorted(clones.items(), key=lambda x:len(x[0]), reverse=True):
    print('<<<<<<<<', file=output)
    print('count {}'.format(clone[1][0]), file=output)
    for file in [file_list[id] for id in clone[1][1]]:
        print('appears in {}'.format(file), file=output)
    print(''.join(clone[0]), file=output)
    print('>>>>>>>>', file=output)
