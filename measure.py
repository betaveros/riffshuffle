from typing import List, Dict, Tuple, Callable

from chord import Chord

class Measure:
	def __init__(self, chord: Chord, chord_name: str, start: float, end: float, reps: int, melody_notes: List[Tuple[int, float]]):
		self.chord = chord
		self.chord_name = chord_name
		self.start = start
		self.end = end
		self.reps = reps
		self.melody_notes = melody_notes
	def __repr__(self):
		return 'Measure(chord={}, chord_name={}, start={}, end={}, reps={}, melody_notes={})'.format(repr(self.chord), repr(self.chord_name), self.start, self.end, self.reps, repr(self.melody_notes))

	def modify_chord(self, f: Callable[[Chord], Chord]) -> 'Measure':
		return Measure(
				chord=f(self.chord),
				chord_name=self.chord_name,
				start=self.start,
				end=self.end,
				reps=self.reps,
				melody_notes=self.melody_notes)

	def transpose(self, semitones: int) -> 'Measure':
		return Measure(
				chord=self.chord.transpose(semitones),
				chord_name=self.chord_name,
				start=self.start,
				end=self.end,
				reps=self.reps,
				melody_notes=[((midi + semitones) % 12, duration) for midi, duration in self.melody_notes])

class Song:
	def __init__(self, name: str, meta: str, measures: List[Measure]):
		self.name = name
		self.meta = meta
		self.measures = measures

	def __repr__(self):
		return 'Song({}, {}, {})'.format(repr(self.name), repr(self.meta), repr(self.measures))

	def modify_chord(self, f: Callable[[Chord], Chord]) -> 'Song':
		return Song(name=self.name, meta=self.meta, measures=[measure.modify_chord(f) for measure in self.measures])

	def transpose(self, semitones: int) -> 'Song':
		return Song(name=self.name, meta=self.meta, measures=[measure.transpose(semitones) for measure in self.measures])
