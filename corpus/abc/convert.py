import sys
sys.path.append('..')
from typing import Optional
from typing_extensions import Literal
from chord import RelativeChord, Chord

note_dict = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}

def identify_note(ch: str) -> int:
	if ch.endswith('#'): return identify_note(ch[:-1]) + 1
	elif ch.endswith('-'): return (identify_note(ch[:-1]) - 1) % 12
	else: return note_dict[ch.lower()]

def convert(symbol: str, major_tonic: int) -> Chord:
	symbol = symbol.replace(' ', '')
	symbol = symbol.replace('+', '#')
	if symbol == '':
		return Chord(None, None)
	bass: Optional[int] = None
	seventh: Literal[None, 'min'] = None
	quality: Literal['maj', 'min'] = 'maj'
	inversions = 0
	if '/' in symbol:
		symbol, bass_str = symbol.split('/')
		bass = identify_note(bass_str)

	def cut(s):
		nonlocal symbol
		if symbol.endswith(s):
			symbol = symbol[:-len(s)]
			return True
		return False

	if cut('7b9') or cut('7'): seventh = 'min'
	cut('6')
	if cut('m'): quality = 'min'
	
	midi = identify_note(symbol)

	try:
		if bass is not None:
			inversions = [x % 12 for x in Chord(midi % 12, RelativeChord(quality, seventh)).render()].index(bass)
	except ValueError: pass

	return Chord((midi - major_tonic) % 12, RelativeChord(quality, seventh, inversions))

def get_chord_type(symbol: str) -> str:
	orig_symbol = symbol

	symbol = symbol.replace(' ', '')
	if symbol == '':
		return 'no chord'
	bass: Optional[int] = None
	seventh: Literal[None, 'min'] = None
	sixth = False
	quality: Literal['maj', 'min'] = 'maj'
	additions = []
	inversions = 0
	if '/' in symbol:
		symbol, bass_str = symbol.split('/')
		bass = identify_note(bass_str)

	def cut(s):
		nonlocal symbol
		if symbol.endswith(s):
			additions.insert(0, s)
			symbol = symbol[:-len(s)]
			return True
		return False

	if cut('7b9'): return orig_symbol
	if cut('7'): seventh = 'min'
	if cut('6'): sixth = True
	if cut('m'): quality = 'min'
	
	midi = identify_note(symbol) # crash if can't figure it out

	bass_annotation = ''
	if bass is not None:
		try:
			inversions = [x % 12 for x in Chord(midi % 12, RelativeChord(quality, seventh)).render()].index(bass)
			if inversions:
				if inversions == 1: ordinal = '1st'
				elif inversions == 2: ordinal = '2nd'
				elif inversions == 3: ordinal = '3rd'
				else: raise Exception('what inversion? {}'.format(inversions))
				bass_annotation = ', {} inversion'.format(ordinal)
		except ValueError:
			# clean me up manually
			bass_annotation = ', semitone {} in bass'.format((bass - midi) % 12)
			print(orig_symbol)
	things = []
	if quality == 'min':
		if seventh == 'min': things.append('minor 7th')
		else: things.append('minor')
	else:
		if seventh == 'min': things.append('dominant 7th')
		else: things.append('major')
	if sixth: things.append(' sixth')
	things.append(bass_annotation)
	return ''.join(things)

def sanity_check(d):
	for chord, freq in d.items():
		try:
			print(chord, convert(chord).to_roman_numeral())
		except KeyError as e:
			raise ValueError(str(chord), e)
		except ValueError as e:
			raise ValueError(str(chord), e)

if __name__ == '__main__':
	sanity_check({'G': 5494, 'D': 5237, 'A': 2380, 'A7': 2099, 'C': 1987, 'D7': 1909, 'Em': 1576, 'Am': 1246, 'E7': 896, 'Bm': 646, 'F': 519, 'G7': 336, 'E': 327, 'Dm': 314, 'Gm': 241, 'B-': 209, 'B7': 196, 'C7': 164, 'F#m': 120, 'D/f#': 104, 'Cm': 83, 'G/b': 69, 'F7': 60, 'F#7': 54, 'E-': 54, 'A7/e': 42, 'A/c#': 39, 'D/a': 26, 'G/d': 21, 'B': 21, 'D7/a': 20, 'A7/c#': 18, 'C/e': 15, 'E7/g#': 15, 'C#m': 13, 'F#': 13, 'D7/f#': 12, 'Am/c': 8, 'Em/g': 8, 'G7/b': 7, 'Gm/d': 7, 'E7/b': 7, 'C6': 6, 'F/a': 5, 'A/e': 5, '': 5, 'Gm/b-': 5, 'Fm': 5, 'Bm/a': 5, 'G7/f': 5, 'C/g': 4, 'Em/d': 4, 'A7/g': 4, 'D7/c': 4, 'B7/f#': 4, 'Dm/a': 3, 'F/c': 3, 'B-/d': 3, 'Em7': 3, 'Am7': 3, 'Am/g': 3, 'Bm7': 3, 'B-7': 3, 'Am/e': 2, 'Am7/g': 2, 'C#7': 2, 'Bm/f#': 2, 'G6': 2, 'G7/d': 2, 'F#m/a': 2, 'Dm6': 2, 'E7b9': 2, 'Dm/f': 2, 'C7/g': 1, 'Bm/d': 1, 'Am/g#': 1, 'Am/f#': 1, 'Cm/g': 1, 'B-/f': 1, 'F7/a': 1, 'A-': 1, 'Em7/d': 1, 'Cm6': 1, 'G#7': 1, 'C#': 1, 'Dm7/c': 1, 'A7/f#': 1, 'D7/b': 1, 'D m': 1, 'D6': 1, 'Em/d#': 1, 'Em/c#': 1, 'C/c': 1, 'D7b9': 1, 'D/c#': 1, 'D/g': 1})
