import os, math, pickle, time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import music21

from measure import Measure, Song
from corpus.abc.convert import convert, get_chord_type

cur_dirname = os.path.dirname(__file__)
abc_dirpath = os.path.join(cur_dirname, 'nottingham-dataset', 'ABC_cleaned')
pickle_path = os.path.join(cur_dirname, 'abc.pickle')

def stats():
	c = 0
	for filename in os.listdir(abc_dirpath):
		if filename.endswith('.abc'):
			print('-', filename)
			for score in music21.converter.parse(os.path.join(abc_dirpath, filename)).getElementsByClass(music21.stream.Score):
				metadatas = score.getElementsByClass(music21.metadata.Metadata)
				assert len(metadatas) == 1
				title = metadatas[0].title
				print(title)
				c += 1
	print(c)

# each "song" is only a song in which the key doesn't change
def parse_songs():
	print("Parsing the Nottingham dataset")
	start_time = time.time()
	songs = []

	for filename in os.listdir(abc_dirpath):
		if filename.endswith('.abc'):
			print('-', filename)
			for score in music21.converter.parse(os.path.join(abc_dirpath, filename)).getElementsByClass(music21.stream.Score):
				# score.show('text')

				metadatas = score.getElementsByClass(music21.metadata.Metadata)
				assert len(metadatas) == 1
				title = metadatas[0].title
				section = 0

				for part in score.getElementsByClass(music21.stream.Part):
					output_measures = []
					output_measure = None

					key = None
					for measure in part.getElementsByClass(music21.stream.Measure):
						for node in measure:
							if isinstance(node, music21.key.Key):
								if output_measure:
									output_measures.append(output_measure)
									output_measure = None
								if output_measures:
									assert key, "No key when dumping song!?"
									songs.append(Song("{}/{}/{}".format(filename, title, section), key.mode, output_measures))
									section += 1
									output_measures = []

								key = node

							elif isinstance(node, music21.harmony.ChordSymbol):
								assert key, "No key before chord!?"

								chord = convert(node._figure, key.tonic.midi)

								if output_measure:
									output_measures.append(output_measure)
								output_measure = Measure(
									chord=chord,
									chord_name="",
									start=node.offset,
									end=node.duration.quarterLength,
									reps=1,
									melody_notes=[],
								)
							elif isinstance(node, music21.note.Note):
								midi = (node.pitch.midi - key.tonic.midi) % 12

								if output_measure:
									output_measure.melody_notes.append((midi, node.duration.quarterLength))
					if output_measure:
						output_measures.append(output_measure)
					if output_measures:
						assert key, "No key when dumping song!?"
						songs.append(Song("{}/{}/{}".format(filename, title, section), key.mode, output_measures))

	print("Done in", time.time() - start_time, "seconds")
	return songs

def tabulate_chord_types() -> Dict[str, int]:
	print("Parsing the Nottingham dataset")
	start_time = time.time()
	chord_type_dict = Counter()

	for filename in os.listdir(abc_dirpath):
		if filename.endswith('.abc'):
			print('-', filename)
			for score in music21.converter.parse(os.path.join(abc_dirpath, filename)).getElementsByClass(music21.stream.Score):
				# score.show('text')

				for part in score.getElementsByClass(music21.stream.Part):
					for measure in part.getElementsByClass(music21.stream.Measure):
						for node in measure:
							if isinstance(node, music21.harmony.ChordSymbol):
								chord_type_dict[get_chord_type(node._figure)] += 1

	print("Done in", time.time() - start_time, "seconds")
	return chord_type_dict

def dump_songs():
	with open(pickle_path, 'wb') as outfile:
		pickle.dump(parse_songs(), outfile)

# helpful: measure.show('text')

def load_songs():
	with open(pickle_path, 'rb') as infile:
		songs = pickle.load(infile)

		major_songs = [song for song in songs if song.meta == 'major']
		minor_songs = [song for song in songs if song.meta == 'minor']

		assert len(major_songs) + len(minor_songs) == len(songs)

		return {
			'all': songs,
			'maj': major_songs,
			'min': minor_songs,
		}
