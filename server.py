#!/usr/bin/env python

import asyncio
import websockets
import json
import traceback

import corpus.rs
import corpus.abc
import corpus.marg
from music21 import roman
from typing import List, Optional
from typing_extensions import Literal
from hmmpredictor import SongStatSet, linearly_mixed_hmm_predict
from chord import Chord

from functools import lru_cache

# import logging
# logger = logging.getLogger('websockets')
# logger.setLevel(logging.INFO)
# logger.addHandler(logging.StreamHandler())

def productionize_chord(chord, key_signature: int, score: float, bottom_bass: int):
	midi_root = (key_signature * 7) % 12
	return {
		"name": chord.chordname(key_signature),
		"score": score,
		"value": chord.relative_to_absolute(key_signature).stringify(),
		"midis": chord.render_offset(midi_root, bottom_bass),
	}

rs_songs = corpus.rs.load_songs()
abc_songs = corpus.abc.load_songs()
marg_songs = corpus.marg.load_songs()
print("loaded songs")

major_songs = rs_songs['maj'] + rs_songs['mix'] + abc_songs['maj'] + marg_songs
minor_songs = rs_songs['min'] + abc_songs['min']

major_songs = [song.modify_chord(lambda chord: chord.beta_collapse()) for song in major_songs]
minor_songs = [song.modify_chord(lambda chord: chord.beta_collapse()) for song in minor_songs]

major_stat_set = SongStatSet.from_songs(major_songs)
parallel_minor_stat_set = SongStatSet.from_songs(minor_songs)
relative_minor_stat_set = SongStatSet.from_songs([song.transpose(-3) for song in minor_songs])

all_chords = list(sorted(set(major_stat_set.all_chords()) | set(parallel_minor_stat_set.all_chords()) | set(relative_minor_stat_set.all_chords())))

# all_stat_set = SongStatSet.from_songs(major_songs + minor_songs)
# minor_in_relative_major_stat_set = SongStatSet.from_songs(major_songs + [song.transpose(-3) for song in minor_songs])

async def echo(websocket, path):
	print("echo!!!")
	async for message in websocket:
		print("message!!!")
		try:
			ans = json.loads(message)
			print(ans)
			seq_number = ans['seq']
			music = ans['music']
			chord_length = ans['chordLength']
			jazziness = ans['jazziness']
			first_weight = ans['firstWeight']
			determinism_weight = ans['determinismWeight']
			seed = ans['seed']
			bottom_bass = ans['bottomBass']

			# this is a p bad name tbh
			constraints = ans['constraints'] # Optional[List[{'time': float, 'value': str, 'locked': bool}]]
			raw_notes = music['notes']
			key_signature = ans['keySignature']
			minorness = ans['minorness']
			tolerance = ans['tolerance']
			mode = ans['mode']
			preserve = ans['preserve'] # preserve even unlocked stuff

			midi_root_of_major = key_signature * 7 % 12
			# even for relative minor we're going to use the major root for simplicity;
			# we can transpose all the data, so it's fine.
			if not constraints:
				last_end = max(note['end'] for note in raw_notes)
				constraints = [{'time': i * chord_length, 'locked': False} for i in range(1 + int(last_end // chord_length))]
				preserve = False

			grouped_notes = []

			notes_ix = 0
			# get all but last measure
			for constraint, next_constraint in zip(constraints, constraints[1:]):
				start = constraint['time']
				end = next_constraint['time']

				group = []
				while notes_ix < len(raw_notes) and raw_notes[notes_ix]['start'] < end - tolerance:
					group.append((raw_notes[notes_ix]['pitch'] - midi_root_of_major) % 12)
					notes_ix += 1
				grouped_notes.append(group)

			# followed by last group
			last_group = []
			while notes_ix < len(raw_notes):
				last_group.append((raw_notes[notes_ix]['pitch'] - midi_root_of_major) % 12)
				notes_ix += 1
			grouped_notes.append(last_group)

			assert len(grouped_notes) == len(constraints)

			print('------------------------')
			print('constraints:', constraints)
			locked_chords = [Chord.parse(constraint['value']).absolute_to_relative(key_signature) if constraint['locked'] else None for constraint in constraints]

			if preserve:
				preserve_chords = [Chord.parse(constraint['value']).absolute_to_relative(key_signature) for constraint in constraints]
			else:
				preserve_chords = None


			if mode == 'major': stat_set_list = [(1.0, major_stat_set)]
			elif mode == 'parallel-minor': stat_set_list = [(1.0, parallel_minor_stat_set)]
			elif mode == 'relative-minor': stat_set_list = [(1.0, relative_minor_stat_set)]
			elif mode == 'mixed-parallel': stat_set_list = [(1.0 - minorness, major_stat_set), (minorness, parallel_minor_stat_set)]
			elif mode == 'mixed-relative': stat_set_list = [(1.0 - minorness, major_stat_set), (minorness, relative_minor_stat_set)]
			else: stat_set_list = [(1.0, major_stat_set)] # ?????

			chords = linearly_mixed_hmm_predict(stat_set_list, grouped_notes, locked_chords, preserve_chords, jazziness=jazziness, seed=seed, first_note_weight=first_weight, determinism_weight=determinism_weight)
			res = []
			for i, ((chord_score, chord), suggestion, scored_chord_list) in enumerate(chords):
				res.append({
					'time': constraints[i]['time'],
					'value': productionize_chord(chord, key_signature, chord_score, bottom_bass),
					'suggestion': productionize_chord(suggestion[1], key_signature, suggestion[0], bottom_bass) if suggestion else None,
					'locked': i < len(locked_chords) and locked_chords[i] is not None,
					'recommendations': [productionize_chord(c, key_signature, s, bottom_bass) for (s, c) in scored_chord_list],
				})
			print('------------------------')
			print('result:', res)
			await websocket.send(json.dumps({
				'seq': seq_number,
				'allChords': [productionize_chord(c, key_signature, 0, bottom_bass) for c in all_chords],
				'result': res,
			}))
		except Exception as e:
			print(e)
			traceback.print_exc()
			await websocket.send(json.dumps({'error': traceback.format_exc()}))

start_server = websockets.serve(echo, "localhost", 8765)

print("starting server in event loop...")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
