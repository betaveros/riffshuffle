from typing import Optional, List
from typing_extensions import Literal
from functools import total_ordering
# A chord without a specified root. We drop sixths, and ninths and higher.

roman_numerals = ['I', 'bII', 'II', 'bIII', 'III', 'IV', '#IV', 'V', 'bVI', 'VI', 'bVII', 'VII']

@total_ordering # really unimportant but lets us break ties consistently
class RelativeChord:
	def __init__(self,
			quality: Literal['maj', 'min', 'dim', 'aug', 'majb5', 'sus2', 'sus4'],
			seventh: Literal[None, 'maj', 'min', 'dim'] = None,
			inversions: int = 0):
		self.quality = quality
		self.seventh = seventh
		self.inversions = inversions

	@property
	def simple_quality(self) -> Literal['maj', 'min']:
		# we treat suspensions as major /shrug
		if self.quality in ['min', 'dim']: return 'min'
		else: return 'maj'

	@property
	def beta_quality(self) -> Literal['maj', 'min', 'dim']:
		if self.quality == 'min': return 'min'
		elif self.quality == 'dim': return 'dim'
		else: return 'maj'

	def rs_collapse(self) -> 'RelativeChord':
		sq = self.simple_quality
		return RelativeChord(sq, 'min' if self.seventh == 'min' and sq == 'maj' else None, 0)

	def beta_collapse(self) -> 'RelativeChord':
		sq = self.beta_quality
		return RelativeChord(sq, 'min' if self.seventh == 'min' and sq in ['min', 'maj'] else None, 0)


	def simplified(self) -> 'RelativeChord':
		return RelativeChord(self.simple_quality)

	def render_offsets(self):
		ret = [0]
		if self.quality == 'maj': ret.extend([4, 7])
		elif self.quality == 'min': ret.extend([3, 7])
		elif self.quality == 'dim': ret.extend([3, 6])
		elif self.quality == 'aug': ret.extend([4, 8])
		elif self.quality == 'majb5': ret.extend([4, 6])
		elif self.quality == 'sus2': ret.extend([2, 7])
		elif self.quality == 'sus4': ret.extend([5, 7])

		if self.seventh == 'maj': ret.append(11)
		elif self.seventh == 'min': ret.append(10)
		elif self.seventh == 'dim': ret.append(9)

		for _ in range(self.inversions):
			ret = ret[1:] + [ret[0] + 12]
		return ret

	def stringify(self):
		return ' '.join([self.quality, str(self.seventh), str(self.inversions)])

	@classmethod
	def parse(cls, s):
		quality, seventh, inversions = s.split()
		if seventh == 'None':
			seventh = None
		inversions = int(inversions)
		return cls(quality, seventh, inversions)

	def __repr__(self):
		return 'RelativeChord(quality={}, seventh={}, inversions={})'.format(repr(self.quality), repr(self.seventh), self.inversions)

	def __eq__(self, other):
		try:
			return self.quality == other.quality and self.seventh == other.seventh and self.inversions == other.inversions
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.quality, self.seventh, self.inversions))

	def __lt__(self, other):
		if isinstance(other, RelativeChord):
			return self.stringify() < other.stringify()
		else:
			return NotImplemented

# ???
class RC:
	maj = RelativeChord('maj')
	min = RelativeChord('min')
	aug = RelativeChord('aug')
	dim = RelativeChord('dim')
	sus2 = RelativeChord('sus2')
	sus4 = RelativeChord('sus4')
	sus47 = RelativeChord('sus4', 'min')
	aug7 = RelativeChord('aug', 'min')
	dom7 = RelativeChord('maj', 'min')
	min7 = RelativeChord('min', 'min')
	maj7 = RelativeChord('maj', 'maj')
	min_maj7 = RelativeChord('min', 'maj')
	dim7 = RelativeChord('dim', 'dim')
	half_dim7 = RelativeChord('dim', 'min')

CIRCLE_OF_FIFTHS = "FCGDAEB" # ["Fb", "Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "E#", "B#"]

def get_pitch_name(relative_semitone: int, key_sig: int) -> str:
	# I think we want to use Ab to C#, and then corresponding ones for other notes
	# Note that 7 is self-inverse mod 12, but clamp it down to -4

	# Offset of this note from the tonic on the circle of fifths
	circle_of_fifths_position = (relative_semitone * 7 + 4) % 12 - 4

	fifths_offset_from_f = key_sig + circle_of_fifths_position + 1
	root = fifths_offset_from_f % 7
	modifier = fifths_offset_from_f // 7
	if modifier < 0:
		return CIRCLE_OF_FIFTHS[root] + '♭' * (-modifier)
	else:
		return CIRCLE_OF_FIFTHS[root] + '♯' * modifier

@total_ordering
class Chord:
	def __init__(self,
			root: Optional[int], # 0 to 11; above tonic. or None for N.C.
			relative_chord: Optional[RelativeChord], # None for pedal...
		):
		self.root = root
		self.relative_chord = relative_chord

	@property
	def simple_quality(self) -> Literal[None, 'maj', 'min']:
		if self.relative_chord is None: return None
		return self.relative_chord.simple_quality

	def render(self) -> List[int]:
		if self.root is None:
			return []
		elif self.relative_chord is None:
			return [self.root]
		else:
			return [self.root + off for off in self.relative_chord.render_offsets()]

	def render_offset(self, offset: int, bottom_bass: int) -> List[int]:
		rendered = self.render()
		if not rendered: return []

		bass = rendered[0]
		new_bass = (bass + offset - bottom_bass) % 12 + bottom_bass
		return [new_bass - bass + note for note in rendered]



	def rs_collapse(self) -> 'Chord':
		return Chord(self.root, self.relative_chord.rs_collapse() if self.relative_chord else None)

	def beta_collapse(self) -> 'Chord':
		return Chord(self.root, self.relative_chord.beta_collapse() if self.relative_chord else None)

	def simplified(self) -> 'Chord':
		return Chord(self.root, self.relative_chord.simplified() if self.relative_chord else None)

	def __repr__(self) -> str:
		return 'Chord({}, {})'.format(self.root, repr(self.relative_chord))

	def __eq__(self, other) -> bool:
		try:
			return self.root == other.root and self.relative_chord == other.relative_chord
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.root, self.relative_chord))

	def __lt__(self, other):
		if isinstance(other, Chord):
			return self.stringify() < other.stringify()
		else:
			return NotImplemented

	def stringify(self) -> str:
		if self.root is None:
			return ''
		elif self.relative_chord is None:
			return str(self.root)
		else:
			return '{:02d}:{}'.format(self.root, self.relative_chord.stringify())

	@classmethod
	def parse(cls, s) -> 'Chord':
		if s == '':
			return cls(None, None)
		elif ':' not in s:
			return cls(int(s), None)
		else:
			root, rest = s.split(':')
			return cls(int(root), RelativeChord.parse(rest))

	def transpose(self, steps: int) -> 'Chord':
		if self.root is None: return self
		return Chord((self.root + steps) % 12, self.relative_chord)

	def relative_to_absolute(self, key_signature: int):
		return self.transpose(key_signature * 7)
	def absolute_to_relative(self, key_signature: int):
		return self.transpose(key_signature * 5)

	def chordname(self, key_signature: int):
		if self.root is None: return 'N.C.'

		base = get_pitch_name(self.root, key_signature)

		if self.relative_chord is None: return base + 'pedal'

		rc = self.relative_chord
		if rc.quality in ['maj', 'majb5', 'sus2', 'sus4']:
			if rc.seventh == None: pass
			elif rc.seventh == 'maj': base += 'maj7'
			elif rc.seventh == 'min': base += '7'
			elif rc.seventh == 'dim': base += '6' # seems fake
			else: raise ValueError('unexpected seventh: {}'.format(rc.seventh))

			if rc.quality == 'majb5': base += 'b5'
			elif rc.quality == 'sus2': base += 'sus2'
			elif rc.quality == 'sus4': base += 'sus4'
		elif rc.quality == 'min':
			if rc.seventh == None: base += 'm'
			elif rc.seventh == 'maj': base += 'minMaj7'
			elif rc.seventh == 'min': base += 'm7'
			elif rc.seventh == 'dim': base += 'm6' # seems fake
			else: raise ValueError('unexpected seventh: {}'.format(rc.seventh))
		elif rc.quality == 'dim':
			if rc.seventh == None: base += 'dim'
			elif rc.seventh == 'maj': base += 'dimMaj7'
			elif rc.seventh == 'min': base += 'dimMin7'
			elif rc.seventh == 'dim': base += 'dim7'
			else: raise ValueError('unexpected seventh: {}'.format(rc.seventh))
		elif rc.quality == 'aug':
			if rc.seventh == None: base += 'aug'
			elif rc.seventh == 'maj': base += 'aug7'
			elif rc.seventh == 'min': base += 'augMin7' # seems fake
			elif rc.seventh == 'dim': base += 'augDim7' # seems really fake
			else: raise ValueError('unexpected seventh: {}'.format(rc.seventh))
		else: raise ValueError('unexpected quality: {}'.format(rc.quality))

		if rc.inversions:
			base += '/' + get_pitch_name(self.render()[rc.inversions], key_signature)

		return base

	def to_roman_numeral(self):
		if self.root is None: return 'N.C.'

		base = roman_numerals[self.root]
		if self.relative_chord is None: return base + 'pedal'

		if self.relative_chord.quality == 'min':
			base = base.lower()
		elif self.relative_chord.quality == 'aug':
			base = base + '+'
		elif self.relative_chord.quality == 'dim':
			base = base.lower()
			if self.relative_chord.seventh == 'min':
				base = base + 'h'
			else:
				base = base + 'o'
		else: # maj, majb5, sus2, sus4
			if self.relative_chord.seventh == 'min':
				base = base + 'd'

		if self.relative_chord.seventh:
			base += ['7', '65', '43', '42'][self.relative_chord.inversions]
		else:
			base += ['', '6', '64'][self.relative_chord.inversions]

		if self.relative_chord.quality == 'sus2':
			base += 's2'
		elif self.relative_chord.quality == 'sus4':
			base += 's4'
		elif self.relative_chord.quality == 'majb5':
			base += 'b5'

		return base

class C:
	all_simple_chords = [Chord(root, rc) for root in range(12) for rc in [RC.maj, RC.min]]
	tonic_major = Chord(0, RC.maj)
	tonic_minor = Chord(0, RC.min)

	I = Chord(0, RC.maj)
	i = Chord(0, RC.min)
	ii = Chord(2, RC.min)
	IV = Chord(5, RC.maj)
	V = Chord(7, RC.maj)
	vi = Chord(9, RC.min)
