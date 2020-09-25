import sys
sys.path.append('..')
from chord import RelativeChord, Chord

# We tracked only the onsets of melodic notes, without any direct indication of the note length. In most cases, this length can be inferred from the onset of the next note.

# Seventh chords: capital Roman numeral plus 7 (e.g. IV7) is a major seventh, lower-case Roman numeral plus 7 (e.g. iv7) is a minor seventh, capital RN plus d7 (e.g. Id7) is a dominant seventh, lower-case RN plus h7 is a half-diminished seventh, lower-case RN plus x7 is a fully diminished seventh. The exception is V7, which indicates a dominant seventh chord. Inversions may be used with any of these: for example, iih65 is a first-inversion half-diminished ii chord.

# Note that all roman numerals are considered on the major mode based on the determined tonal center, though no judgment is made as to whether the piece is really in major or minor (or something else)
# > Roots are assumed to be major-mode scale degrees unless otherwise indicated (p. 55)

roman_numerals = ['I', 'bII', 'II', 'bIII', 'III', 'IV', '#IV', 'V', 'bVI', 'VI', 'bVII', 'VII']

def identify_roman_numeral(symbol): # (midi_semitones, 'maj' | 'min')
	if symbol == 'bV': symbol = '#IV'
	for i, rn in enumerate(roman_numerals):
		if rn == symbol: return (i, 'maj')
		elif rn.lower() == symbol: return (i, 'min')
	raise ValueError("can't identify {}".format(symbol))

def convert(symbol):
	relative_base = 0
	seventh = None
	inversions = 0
	quality_override = None
	if '/' in symbol:
		symbol, base = symbol.split('/')
		relative_base, _ = identify_roman_numeral(base)

	def cut(s):
		nonlocal symbol
		if symbol.endswith(s):
			symbol = symbol[:-len(s)]
			return True
		return False

	if cut('+11'): quality_override = 'aug'; seventh = 'min' # ??
	if cut('b5'): quality_override = 'flat5'
	if cut('s4'): quality_override = 'sus4'

	if cut('64'): inversions = 2
	elif cut('65'): inversions = 1; seventh = '?'
	elif cut('43'): inversions = 2; seventh = '?'
	elif cut('42'): inversions = 3; seventh = '?'
	elif cut('6'): inversions = 1
	elif cut('11'): seventh = '?'
	elif cut('9'): seventh = '?'
	elif cut('7'): seventh = '?'

	if cut('x') or cut('o'):
		quality_override = 'dim'
		if seventh: seventh = 'dim'
	elif cut('d'): seventh = 'min'
	elif cut('h'): quality_override = 'dim'; seventh = 'min'
	elif cut('+'): quality_override = 'aug'
	
	midi, quality = identify_roman_numeral(symbol)
	if seventh == '?':
		if midi == 7 and quality == 'maj': # V7 is dominant, others are not
			seventh = 'min'
		else:
			seventh = quality

	if quality_override == 'flat5':
		if quality == 'maj': quality = 'majb5'
		else: quality = 'dim'
	elif quality_override: quality = quality_override

	return Chord((midi + relative_base) % 12, RelativeChord(quality, seventh, inversions))

def sanity_check(s):
	for line in s.split('\n'):
		chord, count = line.split()
		rn = convert(chord).to_roman_numeral()
		if chord != rn:
			print(chord, rn, count)

# just human-readable
# lol haxx
def get_intermediate_chord_type(symbol: str):
	if '/' in symbol:
		symbol, _base = symbol.split('/')

	additions = []

	def cut(s):
		nonlocal symbol
		if symbol.endswith(s):
			symbol = symbol[:-len(s)]
			additions.insert(0, s)
			return True
		return False

	cut('+11')
	cut('#9')
	cut('b5')
	cut('7b9')
	cut('s4')

	if cut('64'): pass
	elif cut('65'): pass
	elif cut('43'): pass
	elif cut('42'): pass
	elif cut('6'): pass
	elif cut('11'): pass
	elif cut('9'): pass
	elif cut('7'): pass

	if cut('x') or cut('o'): pass
	elif cut('d'): pass
	elif cut('h'): pass
	elif cut('+') or cut('a'): pass

	if symbol == 'V':
		return symbol + ''.join(additions)
	else:
		midi, quality = identify_roman_numeral(symbol)
		return ('I' if quality == 'maj' else 'i') + ''.join(additions)

def get_chord_type(symbol: str):
	x = get_intermediate_chord_type(symbol)
	if x == 'I': return 'major'
	if x == 'I#9': return 'major sharp 9th'
	if x == 'I+9': return 'augmented 9th'
	if x == 'I42': return 'major 7th, 3rd inversion'
	if x == 'I6': return 'major, 1st inversion'
	if x == 'I64': return 'major, 2nd inversion'
	if x == 'I65': return 'major 7th, 1st inversion'
	if x == 'I7': return 'major 7th'
	if x == 'I9': return 'major 9th'
	if x == 'Ib5': return 'major flat 5'
	if x == 'Id43': return 'dominant 7th, 2nd inversion'
	if x == 'Id7': return 'dominant 7th'
	if x == 'Id7#9': return 'dominant 7th sharp 9th'
	if x == 'Id9': return 'dominant 9th'
	if x == 'Is4': return 'suspended 4th'
	if x == 'V': return 'major'
	if x == 'V+11': return 'augmented 11th'
	if x == 'V11': return 'major 11th'
	if x == 'V42': return 'dominant 7th, 3rd inversion'
	if x == 'V43': return 'dominant 7th, 2nd inversion'
	if x == 'V6': return 'major, 1st inversion'
	if x == 'V64': return 'major, 2nd inversion'
	if x == 'V65': return 'dominant 7th, 1st inversion'
	if x == 'V7': return 'dominant 7th'
	if x == 'V7b9': return 'dominant 7th flat 9th'
	if x == 'V7s4': return 'dominant 7th with suspended 4th'
	if x == 'V9': return 'dominant 9th'
	if x == 'Va': return 'augmented'
	if x == 'Va65': return 'augmented 7th, 1st inversion'
	if x == 'Va7': return 'augmented 7th'
	if x == 'Vs4': return 'suspended 4th'
	if x == 'i': return 'minor'
	if x == 'i11': return 'minor 11th'
	if x == 'i42': return 'minor 7th, 3rd inversion'
	if x == 'i43': return 'minor 7th, 2nd inversion'
	if x == 'i6': return 'minor, 1st inversion'
	if x == 'i64': return 'minor 7th'
	if x == 'i65': return 'minor 7th, 1st inversion'
	if x == 'i7': return 'minor 7th'
	if x == 'i7s4': return 'minor 7th with suspended 4th'
	if x == 'i9': return 'minor 9th'
	if x == 'ih42': return 'half-diminished 7th, 3rd inversion'
	if x == 'ih43': return 'half-diminished 7th, 2nd inversion'
	if x == 'ih65': return 'half-diminished 7th, 1st inversion'
	if x == 'ih7': return 'half-diminished 7th'
	if x == 'io': return 'diminished'
	if x == 'io6': return 'diminished, 1st inversion'
	if x == 'is4': return 'suspended 4th'
	if x == 'ix42': return 'diminished 7th, 3rd inversion'
	if x == 'ix43': return 'diminished 7th, 2rd inversion'
	if x == 'ix7': return 'diminished 7th'

if __name__ == '__main__':
	sanity_check("""I 4326
IV 3354
V 2348
i 1424
bVII 1218
vi 944
bVI 623
ii 530
bIII 355
v 219
iv 213
iii 203
IV64 200
V7 192
IV6 154
ii7 132
V6 120
I64 109
I6 101
vi7 92
II 74
IVd7 66
Id7 63
v7 63
iv64 54
iv6 51
V11 47
bII 45
Vs4 41
IV9 39
ii65 38
V/V 30
vi64 30
I7 25
V/ii 24
V/vi 24
iio 23
iii64 21
III 21
bVII6 21
V7/V 20
v64 20
i7 20
V7/vi 19
V+11 18
vii 17
biii 16
iii6 16
V64 15
bV 14
vih7 14
V7/ii 14
iih43 14
viix7/V 13
bVId7 12
IV7 12
V7s4 12
bVI7 12
i6 12
VI 11
bVIId7 11
i9 11
V6/vi 10
vi6 9
bVII9 9
v6 8
V7/iii 8
V9 8
vii64 7
#IV 7
iii7 6
bVIs4 6
V7/IV 6
VId9 6
i42 6
IV65 6
viih7 6
V42/IV 6
IVd43 6
bVI6 6
iih7 5
viix42 5
Id9 5
IV/IV 4
ii/IV 4
bIII6 4
ii7/vi 4
Vs4/vi 4
ii9 4
v65 4
iv65 4
VI7 4
bVII64 4
iih65/ii 4
V42 4
viih7/V 4
ii11 4
bVIb5 4
bVb5 4
i64 4
V43 4
iih65 4
iv7 3
V6/ii 3
vi9 3
viix7/vi 3
ii64 3
viix43/V 3
viio/ii 3
V6/V 3
II7 3
V65/vi 3
bVId7/ii 2
viix43 2
IId7 2
bVId7/V 2
v7s4 2
bIIId7 2
bIII64 2
V7/II 2
bvii7 2
bIII+9 2
viix42/V 2
V65 2
VII 2
V/iii 2
viio/V 1
bIId7 1
V7/bIII 1
II6 1
viio6 1
ii/V 1
bVII/bVII 1
vi/bVII 1
III64 1
V/III 1
V/VII 1
V/bIII 1
iis4 1
V43/ii 1
VId7 1""")
