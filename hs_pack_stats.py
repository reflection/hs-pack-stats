#!/usr/local/bin/python
import json
import os
import re
import sys
import time

""" Continuously write statistics of packs opened from Hearthstone logs to file
    See reddit thread to enable logging
    https://www.reddit.com/r/hearthstone/comments/3i2que/how_to_track_your_pack_openings_for_tomorrows_tgt/

    AllSets.json downloaded from http://hearthstonejson.com
    IMPORTANT: Only tested on a Mac """

stats_file = os.path.expanduser('~/Documents/hs_pack_stats.txt')
hs_log_dir = os.path.expanduser('~/Library/Preferences/Blizzard/Hearthstone/Logs')

# UNTESTED WINDOWS PATHS
# stats_file = os.path.expanduser('~/Documents/hs_pack_stats.txt')
# hs_log_dir = os.path.expanduser('~/Library/Preferences/Blizzard/Hearthstone/Logs')

if not os.path.exists(hs_log_dir):
    sys.exit('Error: Hearthstone log dir does not exist: ' + hs_log_dir)

pack_re = re.compile('.+\[Achievements\] NotifyOfCardGained: \[name=(.+?) cardId=(.+?) type=.+Premium=(.+?)\] (.+)')

# Re-organize Hearthstone json data by ids
hs_data = {}
with open('AllSets.json', 'r') as f:
    data = json.load(f)
    for key in data:
        for d in data[key]:
            hs_data[d.pop('id')] = d

# By default only read latest log file
log = sorted(
    [os.path.join(hs_log_dir, f) for f in os.listdir(hs_log_dir)],
    key=lambda l: os.path.getmtime(l),
    reverse=True
)[0]

stats = {
    'playerClass': { },
    'rarity':      { },
    'type':        { },
    'bling':       {
        'plain':  0,
        'golden': 0,
    },
    'race':        { },
    'dups':  0,
    'total': 0,
}

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

# Update stats file when hs log file is updated
mod_ts = 0
file_pos = -1
while True:
    if os.path.getmtime(log) > mod_ts:
        mod_ts = os.path.getmtime(log)

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

        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

    time.sleep(1)
