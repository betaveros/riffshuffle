import pickle
import os
from collections import defaultdict, Counter
from typing import Dict, List, Iterable, Set, Tuple, TypeVar, Optional
import math
import random

from measure import Measure, Song
from chord import Chord

def compute_seen_log_probs(seen_chords: Dict[Chord, int]) -> Dict[Chord, float]:
	seen_log_probs: Dict[Chord, float] = defaultdict(lambda: -1e3)

	chord_total = sum(seen_chords.values())
	for chord, count in seen_chords.items():
		seen_log_probs[chord] = math.log(count / chord_total)
	return seen_log_probs

def compute_transition_log_probs(seen_chords: Dict[Chord, int], transitions: Dict[Chord, Dict[Chord, int]]) -> Tuple[Dict[Chord, Dict[Chord, float]], Dict[Chord, Dict[Chord, float]]]:
	back_transitions: Dict[Chord, Dict[Chord, int]] = defaultdict(Counter)
	transition_log_probs: Dict[Chord, Dict[Chord, float]] = defaultdict(lambda: defaultdict(lambda: -1e3))
	back_transition_log_probs: Dict[Chord, Dict[Chord, float]] = defaultdict(lambda: defaultdict(lambda: -1e3))

	for chord, next_chords in transitions.items():
		# next_chords: Dict[str, int] (chord -> #)
		# print(chord, next_chords)

		# We're being sneaky here, because chords don't transition out
		# every time we see them; they might be at the end of the piece.
		# So next_total > sum(next_chords.values()), i.e. this isn't
		# actually a probability distribution, but it's proportional to the
		# one we'd expect and makes some math later more reversible.
		next_total: int = seen_chords[chord]
		for next_chord, count in next_chords.items():
			transition_log_probs[chord][next_chord] = math.log(count / next_total)
			back_transitions[next_chord][chord] += count

	for chord, prev_chords in back_transitions.items():
		# ditto
		prev_total: int = seen_chords[chord]
		for prev_chord, count in prev_chords.items():
			back_transition_log_probs[chord][prev_chord] = math.log(count / prev_total)
	
	return (transition_log_probs, back_transition_log_probs)

class SongStatSet:
	def __init__(self,
			seen_log_probs: Dict[Chord, float],
			transition_log_probs: Dict[Chord, Dict[Chord, float]],
			back_transition_log_probs: Dict[Chord, Dict[Chord, float]],
			first_appearances: Dict[Chord, Dict[int, int]], # chord -> semitone -> #. Only counts first note in each chord
			nonfirst_appearances: Dict[Chord, Dict[int, int]], # chord -> semitone -> #. Complement of above
			):

		self.seen_log_probs = seen_log_probs
		self.transition_log_probs = transition_log_probs
		self.back_transition_log_probs = back_transition_log_probs
		self.first_appearances = first_appearances
		self.nonfirst_appearances = nonfirst_appearances

	def all_chords(self):
		return self.seen_log_probs.keys()

	@classmethod
	def from_songs(cls, all_songs: List[Song]):
		seen_chords: Dict[Chord, int] = Counter()
		transitions: Dict[Chord, Dict[Chord, int]] = defaultdict(Counter) # chord -> chord -> #
		first_appearances: Dict[Chord, Dict[int, int]] = defaultdict(Counter) # chord -> semitone -> #
		nonfirst_appearances: Dict[Chord, Dict[int, int]] = defaultdict(Counter) # chord -> semitone -> #

		for song in all_songs:
			prev_measure = None
			for measure in song.measures:
				seen_chords[measure.chord] += measure.reps
				for i, (note, duration) in enumerate(measure.melody_notes):
					if i == 0:
						first_appearances[measure.chord][note] += 1
					else:
						nonfirst_appearances[measure.chord][note] += 1
				if measure.reps > 1:
					transitions[measure.chord][measure.chord] += measure.reps - 1
				if prev_measure:
					transitions[prev_measure.chord][measure.chord] += 1

				prev_measure = measure

		seen_log_probs: Dict[Chord, float] = compute_seen_log_probs(seen_chords)
		transition_log_probs, back_transition_log_probs = compute_transition_log_probs(seen_chords, transitions)
		first_appearances = first_appearances
		nonfirst_appearances = nonfirst_appearances

		return cls(seen_log_probs, transition_log_probs, back_transition_log_probs, first_appearances, nonfirst_appearances)

# viterbi
# input: list of lists of semitones-above-root, each sublist is a measure
# output: list of pairs of chords and lists of chords; the chord is the
# single recommended chord, possibly from a lock and possibly from
# randomization; the sublists are the list of recommended chords for a
# measure, best to worst.


T = TypeVar('T')
T1 = TypeVar('T1')
T2 = TypeVar('T2')

def union_all(sets: Iterable[Iterable[T]]) -> Set[T]:
	s: Set[T] = set()
	return s.union(*sets)

def linearly_mix_dicts(dicts: List[Tuple[float, Dict[T, float]]], default: float) -> Dict[T, float]:
	ret: Dict[T, float] = defaultdict(lambda: default)
	for key in union_all(d.keys() for _weight, d in dicts):
		ret[key] = sum(weight * d[key] for weight, d in dicts)
	return ret

def linearly_mix_dicts_of_dicts(dicts: List[Tuple[float, Dict[T1, Dict[T2, float]]]], default: float, ddict: Dict[T2, float]) -> Dict[T1, Dict[T2, float]]:
	ret: Dict[T1, Dict[T2, float]] = defaultdict(lambda: ddict.copy())
	for key in union_all(d.keys() for _weight, d in dicts):
		ret[key] = linearly_mix_dicts([(weight, d[key]) for weight, d in dicts], default)
	return ret

# wow it's a thing https://en.wikipedia.org/wiki/LogSumExp
def log_sum_exp(xs: List[float]) -> float:
	m = max(xs)
	try:
		s = sum(math.exp(x - m) for x in xs)
		return m + math.log(s)
	except ValueError:
		print('error sad sad sad')
		return -1e3

# actualy we follow mysong in linearly mixing log-domain stats from multiple
# databases
def linearly_mixed_hmm_predict(
		weighted_stat_sets: List[Tuple[float, SongStatSet]],
		measures: List[List[int]],
		locked_chords: List[Optional[Chord]],
		preserve_chords: Optional[List[Chord]],
		number_of_recommendations: int = 10,
		jazziness: float = 0,
		first_note_weight: float = 1.0,
		seed: Optional[int] = None,
		determinism_weight: float = 1.0, # higher means it's "rigged" more towards likelier chords; ignored if seed is None
) -> List[Tuple[Tuple[float, Chord], Optional[Tuple[float, Chord]], List[Tuple[float, Chord]]]]: # (chosen, suggested if different, list of recs) each with score.
	print('predict start')

	# "jazziness" like in MySong. + is more attention to note fit, - is more attention to chord frequencies and progressions
	appearance_weight = 1.0 + jazziness
	transition_weight = 1.0 - jazziness

	weighted_seen_log_probs = linearly_mix_dicts([(stat_weight, stat_set.seen_log_probs) for stat_weight, stat_set in weighted_stat_sets], -1e3)

	# The Problem: we assume P(a|b) = P(ab)/P(b) so, in terms of what we store,
	# P(a|b)P(b) = P(b|a)P(a).
	# But if, say, a appears and b doesn't, this breaks --- P(a|b) and P(b|a)
	# are both the infinitely low probability sentinel.
	# So in that case we can make P(a|b) equal to P(a).

	weighted_transition_log_probs = linearly_mix_dicts_of_dicts([(stat_weight, stat_set.transition_log_probs) for stat_weight, stat_set in weighted_stat_sets], -1e3, weighted_seen_log_probs)
	weighted_back_transition_log_probs = linearly_mix_dicts_of_dicts([(stat_weight, stat_set.back_transition_log_probs) for stat_weight, stat_set in weighted_stat_sets], -1e3, weighted_seen_log_probs)

	# compute the log probs for appearance here, taking into account first note weight
	weighted_appearance_log_probs_list: List[Tuple[float, Dict[Chord, Dict[int, float]]]] = []
	for stat_weight, stat_set in weighted_stat_sets:
		single_appearance_log_probs: Dict[Chord, Dict[int, float]] = defaultdict(lambda: defaultdict(lambda: -1e3))
		for chord in set(stat_set.first_appearances.keys()) | set(stat_set.nonfirst_appearances.keys()):
			first_notes = stat_set.first_appearances[chord]
			nonfirst_notes = stat_set.nonfirst_appearances[chord]

			note_total: float = first_note_weight * sum(first_notes.values()) + sum(nonfirst_notes.values())
			for note in set(first_notes.keys()) | set(nonfirst_notes.keys()):
				weight = first_note_weight * first_notes[note] + nonfirst_notes[note]
				single_appearance_log_probs[chord][note] = math.log(weight / note_total)
		weighted_appearance_log_probs_list.append((stat_weight, single_appearance_log_probs))
	appearance_log_probs_def: Dict[int, float] = defaultdict(lambda: -1e3)
	appearance_log_probs = linearly_mix_dicts_of_dicts(weighted_appearance_log_probs_list, -1e3, appearance_log_probs_def)
	print('mixed')

	all_chords_set = set(appearance_log_probs.keys()) | set(c for c in locked_chords if c)
	if preserve_chords:
		all_chords_set |= set(preserve_chords)
	all_chords = list(all_chords_set)
	print('all', len(all_chords))

	inv_all_chords = {chord: i for i, chord in enumerate(all_chords)}

	# if chord in measure #i, its log prob based on melody alone
	chord_appearance_log_probs_table: List[List[float]] = []
	for i, notes in enumerate(measures):
		row = []
		for chord in all_chords:
			row.append(sum(appearance_log_probs[chord][note] * (first_note_weight if i == 0 else 1) for i, note in enumerate(notes)))
		chord_appearance_log_probs_table.append(row)

	print('app')

	n = len(measures)

	weighted_seen_log_probs_list = [weighted_seen_log_probs[chord] for chord in all_chords]

	weighted_transition_log_probs_table = [[weighted_transition_log_probs[c1][c2] for c2 in all_chords] for c1 in all_chords]
	weighted_back_transition_log_probs_table = [[weighted_back_transition_log_probs[c1][c2] for c2 in all_chords] for c1 in all_chords]

	# if chord in measure #i, the optimal previous chord, OR the locked chord
	# if one is supplied
	best_previous_chord_table: List[List[Optional[Chord]]] = [[None for _ in all_chords] for _ in range(n)]
	# if chord in measure #i, the optimal log prob of chords up to here
	opt_prefix_log_prob_table: List[List[float]] = [[-1e3 for _ in all_chords] for _ in range(n)]
	# if chord in measure #i, the log of total probability of chords up to here (not total of log probabilities)
	total_prefix_log_prob_table: List[List[float]] = [[-1e3 for _ in all_chords] for _ in range(n)]
	print('probs')

	# if chord in measure #i, the optimal next chord, OR the locked chord if
	# one is supplied
	# best_next_chord_table: List[List[Optional[Chord]]] = [[None for _ in all_chords] for _ in range(n)]
	# if chord in measure #i, the optimal log prob of chords hereafter
	opt_suffix_log_prob_table: List[List[float]] = [[-1e3 for _ in all_chords] for _ in range(n)]

	def get_locked_chord_at(i: int) -> Optional[Chord]:
		if 0 <= i < len(locked_chords):
			return locked_chords[i]
		return None

	# The probability that the melody and chord sequence would exist is Π_measures P(melody|chord) * P(c_1) * Π_transitions P(c_i+1|c_i)
	# Note that P(c_1) * Π_transitions P(c_i+1|c_i) = P(c_1) * Π_transitions P(c_i and c_i+1)/P(c_i)
	# = (Π_transitions P(c_i and c_i+1)) / (Π_1<i<n P(c_i)), which is forwards-backwards symmetric

	# forward
	for i in range(n):
		if i == 0:
			for ci, chord in enumerate(all_chords):
				lp = transition_weight * weighted_seen_log_probs_list[ci] + appearance_weight * chord_appearance_log_probs_table[i][ci]
				opt_prefix_log_prob_table[i][ci] = lp
				total_prefix_log_prob_table[i][ci] = lp
		else:
			for ci, chord in enumerate(all_chords):
				# mypy juggling
				prev_locked_chord = get_locked_chord_at(i - 1)
				if prev_locked_chord is not None:
					prev_locked_chord_index = inv_all_chords[prev_locked_chord]
					prev_chord = prev_locked_chord
					pci = prev_locked_chord_index
					prev_log_prob = transition_weight * weighted_transition_log_probs_table[pci][ci] + opt_prefix_log_prob_table[i - 1][prev_locked_chord_index]

					total_prev_log_prob = prev_log_prob
				else:
					prev_chords_and_log_probs = ((prev_chord, transition_weight * weighted_transition_log_probs_table[pci][ci] + opt_prefix_log_prob_table[i - 1][pci]) for pci, prev_chord in enumerate(all_chords))
					prev_chord, prev_log_prob = max(prev_chords_and_log_probs, key=lambda p: p[1])

					total_prev_log_prob = log_sum_exp([
						transition_weight * weighted_transition_log_probs_table[pcii][ci] + total_prefix_log_prob_table[i - 1][pcii]
						for pcii, pci in enumerate(all_chords)
					])

				opt_prefix_log_prob_table[i][ci] = prev_log_prob + appearance_weight * chord_appearance_log_probs_table[i][ci]
				best_previous_chord_table[i][ci] = prev_chord

				total_prefix_log_prob_table[i][ci] = total_prev_log_prob + appearance_weight * chord_appearance_log_probs_table[i][ci]
	print('forward done, backward:')
	# backward
	for i in range(n - 1, -1, -1):
		if i == n - 1:
			for ci, chord in enumerate(all_chords):
				opt_suffix_log_prob_table[i][ci] = transition_weight * weighted_seen_log_probs_list[ci] + appearance_weight * chord_appearance_log_probs_table[i][ci]
		else:
			for ci, chord in enumerate(all_chords):
				next_locked_chord = get_locked_chord_at(i + 1)
				if next_locked_chord is not None:
					next_chord = next_locked_chord
					nci = inv_all_chords[next_chord]
					next_log_prob = transition_weight * weighted_back_transition_log_probs_table[nci][ci] + opt_suffix_log_prob_table[i + 1][nci]
				else:
					next_chords_and_log_probs = ((next_chord, transition_weight * weighted_back_transition_log_probs_table[nci][ci] + opt_suffix_log_prob_table[i + 1][nci]) for nci, next_chord in enumerate(all_chords))
					next_chord, next_log_prob = max(next_chords_and_log_probs, key=lambda p: p[1])
				opt_suffix_log_prob_table[i][ci] = next_log_prob + appearance_weight * chord_appearance_log_probs_table[i][ci]
				# best_next_chord_table[i][ci] = next_chord

	if seed is None:
		# To ward off weird stuff from ties and allow locks, compute one optimal
		# sequence of chords using what we computed.
		last_chord_opt = get_locked_chord_at(n - 1)
		if last_chord_opt is None:
			rev_optimal_progression = [max(all_chords, key=lambda chord: opt_prefix_log_prob_table[n - 1][inv_all_chords[chord]])]
		else:
			rev_optimal_progression = [last_chord_opt]

		# print(opt_prefix_log_prob[(n - 1, chord)])
		for i in range(n - 1, 0, -1):
			chord = rev_optimal_progression[-1]
			c = best_previous_chord_table[i][inv_all_chords[chord]]
			assert c is not None
			rev_optimal_progression.append(c)

		first_chord = rev_optimal_progression[-1]
		last_chord = rev_optimal_progression[0]
		print('best1', max(opt_prefix_log_prob_table[n - 1][inv_all_chords[last_chord]] for chord in all_chords))
		print('best1opt', opt_prefix_log_prob_table[n - 1][inv_all_chords[last_chord]])
		print('best2', max(opt_suffix_log_prob_table[0][inv_all_chords[chord]] for chord in all_chords))
		print('best2opt', opt_suffix_log_prob_table[0][inv_all_chords[first_chord]])
		print('1opt <-', opt_prefix_log_prob_table[0][inv_all_chords[first_chord]])
		print('actual')
		op = list(reversed(rev_optimal_progression))
		lpp = 0.0
		for i, chord in enumerate(op):
			ci = inv_all_chords[chord]
			w = appearance_weight * chord_appearance_log_probs_table[i][ci]
			print('appearance', w)
			lpp += w
			if i:
				w = transition_weight * weighted_transition_log_probs_table[inv_all_chords[op[i-1]]][ci]
				print('transition', w)
				lpp += w
			else:
				w = transition_weight * weighted_seen_log_probs_list[ci]
				print('base', w)
				lpp += w
		print(lpp)

		lpp = 0.0
		for i, chord in reversed(list(enumerate(op))):
			ci = inv_all_chords[chord]
			w = appearance_weight * chord_appearance_log_probs_table[i][ci]
			print('appearance', w)
			lpp += w
			if i != n - 1:
				w = transition_weight * weighted_back_transition_log_probs[op[i+1]][chord]
				print('transition', w)
				lpp += w
			else:
				w = transition_weight * weighted_seen_log_probs_list[ci]
				print('base', w)
				lpp += w
		print(lpp)
		suggested_progression = list(reversed(rev_optimal_progression))
	else:
		rng = random.Random()
		rng.seed(seed)

		last_chord_opt = get_locked_chord_at(n - 1)
		if last_chord_opt is None:
			last_chord, = rng.choices(all_chords, weights=[
				math.exp(determinism_weight * total_prefix_log_prob_table[n - 1][ci])
				for ci, chord in enumerate(all_chords)
			])
		else:
			last_chord = last_chord_opt

		rev_chosen_progression = [last_chord]
		for i in range(n - 1, 0, -1):
			next_chord = rev_chosen_progression[-1]
			nci = inv_all_chords[next_chord]

			next_last_chord = get_locked_chord_at(i - 1)
			if next_last_chord is None:
				next_last_chord, = rng.choices(all_chords, weights=[
					math.exp(determinism_weight * (
						total_prefix_log_prob_table[i - 1][ci] +
						transition_weight * weighted_transition_log_probs_table[ci][nci]
					))
					for ci, chord in enumerate(all_chords)
				])

			rev_chosen_progression.append(next_last_chord)

		suggested_progression = list(reversed(rev_chosen_progression))

	print('gonna rec')

	# However, we want to recommend chords.
	ret = []

	def score(i: int, chord: Chord) -> float:
		"""the optimal log prob if chord is at position i
		
		obeying all locked chords except the chord at position i itself;
		subject to rounding error"""

		ci = inv_all_chords[chord]
		return (
			opt_prefix_log_prob_table[i][ci]
			+ opt_suffix_log_prob_table[i][ci]
			- transition_weight * weighted_seen_log_probs[chord]
			- appearance_weight * chord_appearance_log_probs_table[i][ci]
		)
	for i in range(n):
		scored_chords = list(reversed(sorted([(score(i, chord), chord) for chord in all_chords])[-number_of_recommendations:]))
		max_score = scored_chords[0][0]
		rescored_chords = [(math.exp(s - max_score), chord) for s, chord in scored_chords]
		suggested_chord = suggested_progression[i]
		chosen_chord = preserve_chords[i] if preserve_chords else suggested_chord
		scored_suggested = (math.exp(score(i, suggested_chord) - max_score), suggested_chord)
		scored_chosen = (math.exp(score(i, chosen_chord) - max_score), chosen_chord)

		# FIXME lol
		if scored_chosen not in rescored_chords:
			rescored_chords[-1] = scored_chosen
			if scored_suggested not in rescored_chords:
				rescored_chords[-2] = scored_suggested
		elif scored_suggested not in rescored_chords:
			if scored_chosen == rescored_chords[-1]:
				rescored_chords[-2] = scored_suggested
			else:
				rescored_chords[-1] = scored_suggested

		# for mypy
		ret_scored_suggested = None if scored_suggested == scored_chosen else scored_suggested

		ret.append((scored_chosen, ret_scored_suggested, rescored_chords))
	print('retting')
	return ret
