import os, os.path, sys, math, functools, pickle, time
from typing import List, Dict, Tuple
from collections import defaultdict, Counter
import music21
import numpy as np

from measure import Measure, Song
from chord import Chord, C
from corpus.rs.convert import convert, get_chord_type

cur_dirname = os.path.dirname(__file__)
pickle_path = os.path.join(cur_dirname, 'rs.pickle')

def parse_songs() -> List[Song]:
	print("Parsing Temperley and deClercq's 200-song Rock Corpus")
	start_time = time.time()
	songs = []
	# chord_counter = Counter()
	for melody_filename in os.listdir(os.path.join(cur_dirname, 'rs200_melody_nlt')):
		if melody_filename.endswith('.nlt'):
			harmony_filename = melody_filename[:-4] + '.clt'
			melody_path = os.path.join(cur_dirname, 'rs200_melody_nlt', melody_filename)
			harmony_path = os.path.join(cur_dirname, 'rs200_harmony_clt', harmony_filename)
			with open(melody_path) as melody_infile:
				melody_lines = list(melody_infile)
			with open(harmony_path) as harmony_infile:
				harmony_lines = list(harmony_infile)

			melody_ranges: List[Tuple[int, int, int]] = [] # (start, end, semitones)
			if melody_lines:
				last_note = None
				last_note_t = None

				for line in melody_lines:
					line = line.strip()

					if line.startswith('Error:'): continue

					if line.endswith('End'):
						real_t, measure_t_s, _ = line.split()
						measure_t = float(measure_t_s)

						if last_note is not None:
							melody_ranges.append((last_note_t, measure_t, last_note))
					else:
						real_t, measure_t_s, melody_midi_s, semitones_above_root_s = line.split()
						measure_t = float(measure_t_s)
						melody_midi = int(melody_midi_s)
						semitones_above_root = int(semitones_above_root_s)

						if last_note is not None:
							melody_ranges.append((last_note_t, measure_t, last_note))

						last_note = semitones_above_root
						last_note_t = measure_t
			else:
				# Six songs don't have melodies.
				print("-", melody_filename, "no melody")

			measures: List[Measure] = []
			if harmony_lines:
				# has_major_I = False
				# has_minor_i = False

				last_chord = None
				last_chord_name = None
				last_chord_t = None

				for line in harmony_lines:
					line = line.strip()

					if line.endswith('End'):
						# last chord ends
						real_t, measure_t_s, _end = line.split()
						measure_t = float(measure_t_s)

						assert last_chord
						measures.append(Measure(
							chord=last_chord,
							chord_name=last_chord_name,
							start=last_chord_t,
							end=measure_t,
							reps=max(1, int(measure_t) - int(last_chord_t)),
							melody_notes=[],
						))
					else:
						# chord is a string like "I64"
						# chromatic root = integer of root in relation to the current key, adjusted for applied chords (e.g. I=0, bII=1, II=2; V/ii = VI = 9)
						# diatonic root = diatonic category of chromatic root, e.g. VI = 6
						# key = integer of current tonic, e.g. C = 0, C#/Db = 1
						# absolute root = chromatic root + key, e.g. V in D = A = 9

						real_t, measure_t_s, chord_name, chrom_root, diatonic_root, key, abs_root = line.split()
						measure_t = float(measure_t_s)

						# chord_counter[chord_name] += 1
						chord = convert(chord_name)

						# if chord_name == 'i' or chord_name == 'i7': has_minor_i = True
						# elif chord_name == 'I' or chord_name == 'Id7' or chord_name == 'I7': has_major_I = True

						if last_chord:
							measures.append(Measure(
								chord=last_chord,
								chord_name=last_chord_name,
								start=last_chord_t,
								end=measure_t,
								reps=min(4, max(1, int(measure_t) - int(last_chord_t))),
								melody_notes=[],
							))

						last_chord = chord
						last_chord_name = chord_name
						last_chord_t = measure_t

			if measures:
				for i, next_measure in enumerate(measures):
					while melody_ranges and melody_ranges[0][0] < next_measure.start:
						# actually note belongs in the previous measure
						start, end, semitones = melody_ranges.pop(0)
						if i > 0:
							measures[i-1].melody_notes.append((semitones, end - start))

				while melody_ranges:
					start, end, semitones = melody_ranges.pop(0)
					measures[-1].melody_notes.append((semitones, end - start))
				songs.append(Song(melody_filename, '', measures))

	print("Done in", time.time() - start_time, "seconds")
	return songs

def tabulate_chord_types(count_reps: bool) -> Dict[str, int]:
	print("Parsing Temperley and deClercq's 200-song Rock Corpus")
	start_time = time.time()
	songs = []
	chord_type_dict = Counter()
	# even songs with no melody! both transcriptions!
	for harmony_filename in os.listdir(os.path.join(cur_dirname, 'rs200_harmony_clt')):
		if harmony_filename.endswith('.clt'):
			harmony_path = os.path.join(cur_dirname, 'rs200_harmony_clt', harmony_filename)
			with open(harmony_path) as harmony_infile:
				harmony_lines = list(harmony_infile)

			last_chord_name = None
			last_chord_t = None

			for line in harmony_lines:
				line = line.strip()

				if line.endswith('End'):
					# last chord ends
					real_t, measure_t_s, _end = line.split()
					measure_t = float(measure_t_s)

					assert last_chord_name

					reps = max(1, int(measure_t) - int(last_chord_t)) if count_reps else 1
					chord_type_dict[get_chord_type(last_chord_name)] += reps

				else:
					# chord is a string like "I64"
					# chromatic root = integer of root in relation to the current key, adjusted for applied chords (e.g. I=0, bII=1, II=2; V/ii = VI = 9)
					# diatonic root = diatonic category of chromatic root, e.g. VI = 6
					# key = integer of current tonic, e.g. C = 0, C#/Db = 1
					# absolute root = chromatic root + key, e.g. V in D = A = 9

					real_t, measure_t_s, chord_name, chrom_root, diatonic_root, key, abs_root = line.split()
					measure_t = float(measure_t_s)

					if last_chord_name:
						reps = max(1, int(measure_t) - int(last_chord_t)) if count_reps else 1
						chord_type_dict[get_chord_type(last_chord_name)] += reps

					last_chord_name = chord_name
					last_chord_t = measure_t

	print("Done in", time.time() - start_time, "seconds")
	return chord_type_dict

def dump_songs():
	with open(pickle_path, 'wb') as outfile:
		pickle.dump(parse_songs(), outfile)

def load_songs():
	with open(pickle_path, 'rb') as infile:
		songs = pickle.load(infile)

	major_songs = []
	minor_songs = []
	mixed_songs = []

	for song in songs:
		has_major = False
		has_minor = False
		for measure in song.measures:
			sc = measure.chord.simplified()
			if sc == C.tonic_major:
				has_major = True
			elif sc == C.tonic_minor:
				has_minor = True
		assert has_major or has_minor
		if has_major:
			if has_minor:
				mixed_songs.append(song)
			else:
				major_songs.append(song)
		else:
			minor_songs.append(song)
	
	return {
		'all': songs,
		'maj': major_songs,
		'min': minor_songs,
		'mix': mixed_songs,
	}
