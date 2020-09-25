import os, csv, pickle, time
from typing import List, Dict, Tuple, Union
from typing_extensions import Literal
from collections import defaultdict, Counter
import music21

from measure import Measure, Song
from chord import RelativeChord, RC, Chord

cur_dirname = os.path.dirname(__file__)
pickle_path = os.path.join(cur_dirname, 'marg.pickle')
marg_test_dirpath = os.path.join(cur_dirname, 'csv_test')
marg_train_dirpath = os.path.join(cur_dirname, 'csv_train')

scale = "C0 C# D0 D# E0 F0 F# G0 G# A0 A# B0 B#".split()

def unscale(note):
	try:
		return scale.index(note)
	except ValueError:
		return None

chord_merger: Dict[str, Union[RelativeChord, Literal['NC', 'pedal']]] = {
	'[]': 'NC',
	'major': RC.maj,
	'minor': RC.min,
	'dominant': RC.dom7,
	'minor-seventh': RC.min7,
	'minor-sixth': RC.min,
	'dominant-ninth': RC.dom7,
	'augmented': RC.aug,
	'augmented-seventh': RC.aug7,
	'major-seventh': RC.maj7,
	'major-sixth': RC.maj,
	'suspended-fourth': RC.sus4,
	'minor-major': RC.min_maj7,
	'diminished': RC.dim,
	'dominant-seventh': RC.dom7,
	'major-ninth': RC.maj7,
	'': 'NC',
	'half-diminished': RC.half_dim7,
	'minor-ninth': RC.min7,
	'minor-11th': RC.min7,
	'diminished-seventh': RC.dim7,
	'power': RC.maj, # sketchy
	'dominant-11th': RC.dom7,
	'dominant-13th': RC.dom7,
	'maj': RC.maj,
	'7': RC.dom7,
	'min': RC.min,
	'min7': RC.min7,
	'major-minor': RC.dom7, # this just means dominant, right?
	'dim': RC.dim,
	'dim7': RC.dim7,
	'maj7': RC.maj7,
	'minMaj7': RC.min_maj7, # CmM7
	'sus47': RC.sus47, # Csus47
	'suspended-second': RC.sus2,
	'9': RC.dom7,
	'aug': RC.aug,
	'augmented-ninth': RC.aug7,
	'm7b5': RC.half_dim7,
	'6': RC.maj,
	'maj9': RC.maj7, # CMaj9
	'maj69': RC.maj7, #??? https://chords.gock.net/chords/major-six-nine
	' dim7': RC.dim7,
	'minor-13th': RC.min7,
	'min9': RC.min7,
	'pedal': 'pedal',
}

def parse_songs() -> List[Song]:
	print("Parsing CSV Leadsheet Database from MARG (Seoul National University)")
	start_time = time.time()
	songs: List[Song] = []
	for dirpath in [marg_train_dirpath, marg_test_dirpath]:
		print('-', dirpath)
		for filename in os.listdir(dirpath):
			if filename.endswith('.csv'):
				with open(os.path.join(dirpath, filename)) as infile:
					csv_reader = csv.DictReader(infile)
					measure_label = None
					measure = None
					measures = []
					i = 0
					for row in csv_reader:
						# this is not always an integer
						# sometimes it's X1; I don't know what that means
						tonic = 7 * int(row["key_fifths"]) % 12 # note that this is the tonic of the relative major (we're taking C for A minor)
						# not that this *should* be a problem since the paper
						# says all songs are in major key... :thinking:
						mode = row["key_mode"]
						abs_note_root = unscale(row["note_root"])
						if abs_note_root is not None:
							rel_note_root = (abs_note_root - tonic) % 12
						else:
							rel_note_root = None

						melody_note = (rel_note_root, float(row["note_duration"]))

						if row["measure"] != measure_label:
							if measure is not None:
								measures.append(measure)
							measure_label = row["measure"]

							chord_root = unscale(row["chord_root"])
							if chord_root is not None:
								relative_chord_root: int = (chord_root - tonic) % 12
								relative_chord = chord_merger[row["chord_type"]]
								if isinstance(relative_chord, str):
									if relative_chord == 'NC':
										chord = Chord(None, None)
									else:
										chord = Chord(relative_chord_root, None)
								else:
									chord = Chord(relative_chord_root, relative_chord)
							else:
								chord = Chord(None, None)

							# TODO: sometimes chords probably change in a measure idk

							measure = Measure(
								chord=chord,
								chord_name=row["chord_type"],
								start=float(i),
								end=float(i),
								reps=1,
								melody_notes=[melody_note],
							)
						else:
							assert measure is not None
							measure.melody_notes.append(melody_note)
					if measure is not None:
						measures.append(measure)
				songs.append(Song(filename, mode, measures))
	print("Done in", time.time() - start_time, "seconds")
	return songs

def tabulate_chord_types() -> Dict[str, int]:
	print("statsing CSV Leadsheet Database from MARG (Seoul National University)")
	start_time = time.time()
	chord_type_dict = Counter()
	for dirpath in [marg_train_dirpath, marg_test_dirpath]:
		print('-', dirpath)
		for filename in os.listdir(dirpath):
			if filename.endswith('.csv'):
				with open(os.path.join(dirpath, filename)) as infile:
					csv_reader = csv.DictReader(infile)
					last_measure_label = None
					last_chord = None
					for row in csv_reader:
						if row["measure"] != last_measure_label or last_chord != row["chord_type"]:
							last_measure_label = row["measure"]
							last_chord = row["chord_type"]

							chord_type_dict[row["chord_type"]] += 1

	return chord_type_dict

def dump_songs():
	with open(pickle_path, 'wb') as outfile:
		pickle.dump(parse_songs(), outfile)

def load_songs():
	with open(pickle_path, 'rb') as infile:
		songs = pickle.load(infile)
	return songs
