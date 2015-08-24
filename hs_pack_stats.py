import json
import os
import re
import sys
import time
from collections import OrderedDict

""" Hearthstone Pack Statistics Tracker """

# Mac Paths
stats_file = os.path.expanduser('~/Documents/hs_pack_stats.txt')
hs_log_dir = os.path.expanduser('~/Library/Preferences/Blizzard/Hearthstone/Logs')

if not os.path.exists(hs_log_dir):
    sys.exit('Error: Hearthstone log dir does not exist: ' + hs_log_dir)

# By default only read latest log file
log = sorted(
    [os.path.join(hs_log_dir, f) for f in os.listdir(hs_log_dir)],
    key=lambda l: os.path.getmtime(l),
    reverse=True
)[0]

# Windows Paths (untested)
# IMPORTANT: Comment out all lines above this
# stats_file = os.path.expanduser('~\\My Documents\\hs_pack_stats.txt')
# log = os.path.expanduser('~\\AppData\\Local\\Blizzard\\Hearthstone\\Logs\\Power.log')

# Re-organize Hearthstone json data by ids
hs_data = {}
with open('AllSets.json', 'r') as f:
    data = json.load(f)
    for key in data:
        for d in data[key]:
            hs_data[d.pop('id')] = d

pack_re = re.compile('.+\[Achievements\] NotifyOfCardGained: \[name=(.+?) cardId=(.+?) type=.+Premium=(.+?)\] (.+)')
stats = OrderedDict([
    ('rarity',      {}),
    ('playerClass', {}),
    ('type',        {}),
    ('race',        {}),
    ('bling',       {
        'plain':  0,
        'golden': 0,
    }),
    ('dups',        0),
    ('total',       0)
])

def update_hs_stats(card_id):
    for k in stats.keys():
        v = None
        if k in hs_data[card_id]:
            v = hs_data[card_id][k]
        elif k == 'playerClass':
            v = 'Neutral'
        if v:
            if v not in stats[k]:
                stats[k][v] = 0
            stats[k][v] += 1

# Sort everything alphabetically
# except for Class - Neutral (sort to the end)
def custom_sort(a, b):
    if a == 'Neutral':
        a = 'ZZZ'
    if b == 'Neutral':
        b = 'ZZZ'
    if a > b:
        return 1
    return -1
def format_stats(stats, fs, total, level=0):
    length = 14
    keys = stats.keys()
    if level > 0:
        keys.sort(cmp=custom_sort)
    for k in keys:
        if k == 'playerClass':
            name = 'Class'
        else:
            name = k.capitalize()
        if isinstance(stats[k], (int, long)):
            indent = 2 * level
            pad = length - len(name) - indent
            pct = 0
            if total > 0:
                pct = (float(stats[k]) / total) * 100
            fs.append(' ' * indent + '{name}{v: {pad}} ({pct:.2f}%)'.format(
                name=name, v=stats[k], pad=pad, pct=pct
            ))
        else:
            fs.append(name)
            format_stats(stats[k], fs, total, level+1)
        if level == 0:
            fs.append('')
    return fs

# Update stats file when hs log file is updated
file_mod = 0
file_pos = -1
while True:
    if os.path.getmtime(log) > file_mod:
        file_mod = os.path.getmtime(log)

        with open(log, 'r') as f:
            if file_pos > 0:
                f.seek(file_pos)
            for line in f:
                m = pack_re.match(line)
                if m:
                    name, card_id, golden, owned = (
                        m.group(1),
                        m.group(2),
                        True if m.group(3) == 'GOLDEN' else False,
                        int(m.group(4))
                    )
                    # Filter out cards not received from packs
                    card_set, _ = card_id.split('_')
                    if card_set not in ('EX1', 'GVG', 'AT'):
                        continue
                    if card_set == 'EX1' and \
                       'howToGet' in hs_data[card_id] or \
                       'howToGetGold' in hs_data[card_id]:
                        continue
                    # Update stats using Hearthstone data
                    update_hs_stats(card_id)
                    # Update stats outside of Hearthstone data
                    if golden:
                        stats['bling']['golden'] += 1
                    else:
                        stats['bling']['plain'] += 1
                    if owned > 2:
                        stats['dups'] += 1
                    stats['total'] += 1
            file_pos = f.tell()

        fs = []
        fs = '\n'.join(format_stats(stats, fs, stats['total']))
        print fs
        with open(stats_file, 'w') as f:
            f.write(fs)

    time.sleep(1)
