import sys
sys.path.append('..')
from collections import defaultdict, Counter
from chord import Chord, C, RelativeChord, RC
import corpus.rs as rs
import corpus.abc as abc
import corpus.marg as marg
import numpy as np

rs_song_dict = rs.load_songs()
abc_song_dict = abc.load_songs()
marg_songs = marg.load_songs()

def count_tonic_root_triads(songs):
	d = [[0,0],[0,0]]
	for song in songs:
		has_major = any(measure.chord.simplified() == C.I for measure in song.measures)
		has_minor = any(measure.chord.simplified() == C.i for measure in song.measures)
		d[has_major][has_minor] += 1
	print(d)

def show_corrs(title, songs):
	print('=' * 32, title)
	all_chords = C.all_simple_chords
	# a = np.array([[sum(measure.reps or (1/0) for measure in song.measures if measure.chord.simplified() == chord) for song in songs] for chord in all_chords])
	a = np.array([[any(measure.chord.simplified() == chord for measure in song.measures) for song in songs] for chord in all_chords])
	for i1, c1 in enumerate(all_chords):
		for i2, c2 in enumerate(all_chords):
			if i1 < i2:
				corr = np.corrcoef(a[i1], a[i2])
				assert corr.shape == (2, 2)
				corr = corr[0,1]
				if abs(corr) > 0.3:
					print(c1.to_roman_numeral(), c2.to_roman_numeral(), corr)

def count_chord_frac(song, chord):
	chord_counter = Counter()
	total = 0
	for measure in song.measures:
		chord_counter[measure.chord.simplified()] += measure.reps
		total += measure.reps
	return chord_counter[chord] / total

def show_stats(title, songs):
	print('=' * 32, title)
	chord_counter = Counter()
	for song in songs:
		for measure in song.measures:
			chord_counter[measure.chord.simplified()] += measure.reps
	for k, v in sorted(chord_counter.items(), key=lambda p: -p[1]):
		print("{:10} {:10} {:7.02f}% {}".format(k.to_roman_numeral(), v,
			*max((100*count_chord_frac(song, k), song.name) for song in songs)))

	ii = Chord(2, RC.min) # (that's 2 semitones, which is coincidentally ii)
	IV = Chord(5, RC.maj)
	for percent, song_name in sorted((100*count_chord_frac(song, ii), song.name) for song in songs)[-100:]:
		print("      {:7.02f}% {}".format(percent, song_name))
	for percent, song_name in sorted((100*count_chord_frac(song, IV), song.name) for song in songs)[-100:]:
		print("      {:7.02f}% {}".format(percent, song_name))

def count_rc_frac(song, rc):
	chord_counter = Counter()
	total = 0
	for measure in song.measures:
		chord_counter[measure.chord.relative_chord] += measure.reps
		total += measure.reps
	return chord_counter[rc] / total

def show_stats_2(title, songs):
	print('=' * 32, title)
	chord_counter = Counter()
	for song in songs:
		for measure in song.measures:
			chord_counter[measure.chord.relative_chord] += measure.reps
	for k, v in sorted(chord_counter.items(), key=lambda p: -p[1]):
		print("{:10} {:10} {:7.02f}% {}".format(k.stringify() if k else '-', v,
			*max((100*count_rc_frac(song, k), song.name) for song in songs)))

count_tonic_root_triads(rs_song_dict['all'])

# c = 0
# for song in marg_songs:
# 	if song.meta == 'minor': print(song.name); c += 1
# print(c)
# print(len(rs_song_dict['all']))
# print(len(abc_song_dict['all']))
# print(len(marg_songs))

# show_stats_2('rs', rs_song_dict['all'])
# # show_stats_2('rs maj', rs_song_dict['maj'])
# # show_stats_2('rs min', rs_song_dict['min'])
# # show_stats_2('rs mixed', rs_song_dict['mix'])
# show_stats_2('abc', abc_song_dict['all'])
# # show_stats_2('abc maj', abc_song_dict['maj'])
# # show_stats_2('abc min', abc_song_dict['min'])
show_stats('marg', marg_songs)
