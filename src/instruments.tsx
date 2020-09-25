import React, { Component, Fragment } from "react";

import classnames from "classnames";

type InstrumentDialogProps = {
	musicInstrument: number;
	chordInstrument: number;
	onMusicInstrumentChange: (instr: number) => void;
	onChordInstrumentChange: (instr: number) => void;
	onClose: () => void;
	visible: boolean;
};

type InstrumentEntry = { name: string; id: number; }
type InstrumentCategory = { name: string; instruments: Array<InstrumentEntry>; }

// these are not actually MIDI numbers LOL
// https://surikov.github.io/webaudiofont/#catalog-of-instruments
//
export const DEFAULT_MUSIC_INSTRUMENT = 58;
export const DEFAULT_CHORD_INSTRUMENT = 43;

const INSTRUMENTS: Array<InstrumentCategory> = [
	{ name: "Piano", instruments: [
		{ name: "Acoustic Grand Piano", id: 0 },
		{ name: "Bright Acoustic Piano", id: 11 },
		{ name: "Electric Grand Piano", id: 22 },
		{ name: "Honky-tonk Piano", id: 32 },
		{ name: "Electric Piano 1", id: 43 },
		{ name: "Electric Piano 2", id: 58 },
		{ name: "Harpsichord", id: 70 },
		{ name: "Clavinet", id: 81 },
	] },
	{ name: "Chromatic Percussion", instruments: [
		{ name: "Celesta", id: 89 },
		{ name: "Glockenspiel", id: 99 },
		{ name: "Music Box", id: 107 },
		{ name: "Vibraphone", id: 116 },
		{ name: "Marimba", id: 124 },
		{ name: "Xylophone", id: 133 },
		{ name: "Tubular Bells", id: 141 },
		{ name: "Dulcimer", id: 152 },
	] },
	{ name: "Organ", instruments: [
		{ name: "Drawbar Organ", id: 160 },
		{ name: "Percussive Organ", id: 170 },
		{ name: "Rock Organ", id: 180 },
		{ name: "Church Organ", id: 190 },
		{ name: "Reed Organ", id: 200 },
		{ name: "Accordion", id: 211 },
		{ name: "Harmonica", id: 223 },
		{ name: "Tango Accordion", id: 231 },
	] },
	{ name: "Guitar", instruments: [
		{ name: "Acoustic Guitar (nylon)", id: 244 },
		{ name: "Acoustic Guitar (steel)", id: 256 },
		{ name: "Electric Guitar (jazz)", id: 274 },
		{ name: "Electric Guitar (clean)", id: 286 },
		{ name: "Electric Guitar (muted)", id: 299 },
		{ name: "Overdriven Guitar", id: 315 },
		{ name: "Distortion Guitar", id: 333 },
		{ name: "Guitar Harmonics", id: 354 },
	] },
	{ name: "Bass", instruments: [
		{ name: "Acoustic Bass", id: 366 },
		{ name: "Electric Bass (finger)", id: 375 },
		{ name: "Electric Bass (pick)", id: 384 },
		{ name: "Fretless Bass", id: 393 },
		{ name: "Slap Bass 1", id: 401 },
		{ name: "Slap Bass 2", id: 409 },
		{ name: "Synth Bass 1", id: 418 },
		{ name: "Synth Bass 2", id: 434 },
	] },
	{ name: "Strings", instruments: [
		{ name: "Violin", id: 447 },
		{ name: "Viola", id: 458 },
		{ name: "Cello", id: 466 },
		{ name: "Contrabass", id: 475 },
		{ name: "Tremolo Strings", id: 483 },
		{ name: "Pizzicato Strings", id: 492 },
		{ name: "Orchestral Harp", id: 500 },
		{ name: "Timpani", id: 508 },
	] },
	{ name: "Ensemble", instruments: [
		{ name: "String Ensemble 1", id: 517 },
		{ name: "String Ensemble 2", id: 544 },
		{ name: "Synth Strings 1", id: 553 },
		{ name: "Synth Strings 2", id: 567 },
		{ name: "Choir Aahs", id: 576 },
		{ name: "Voice Oohs", id: 588 },
		{ name: "Synth Choir", id: 600 },
		{ name: "Orchestra Hit", id: 608 },
	] },
	{ name: "Brass", instruments: [
		{ name: "Trumpet", id: 617 },
		{ name: "Trombone", id: 624 },
		{ name: "Tuba", id: 632 },
		{ name: "Muted Trumpet", id: 640 },
		{ name: "French Horn", id: 648 },
		{ name: "Brass Section", id: 659 },
		{ name: "Synth Brass 1", id: 671 },
		{ name: "Synth Brass 2", id: 683 },
	] },
	{ name: "Reed", instruments: [
		{ name: "Soprano Sax", id: 695 },
		{ name: "Alto Sax", id: 703 },
		{ name: "Tenor Sax", id: 712 },
		{ name: "Baritone Sax", id: 721 },
		{ name: "Oboe", id: 729 },
		{ name: "English Horn", id: 737 },
		{ name: "Bassoon", id: 745 },
		{ name: "Clarinet", id: 754 },
	] },
	{ name: "Pipe", instruments: [
		{ name: "Piccolo", id: 762 },
		{ name: "Flute", id: 771 },
		{ name: "Recorder", id: 781 },
		{ name: "Pan Flute", id: 789 },
		{ name: "Blown bottle", id: 800 },
		{ name: "Shakuhachi", id: 811 },
		{ name: "Whistle", id: 821 },
		{ name: "Ocarina", id: 829 },
	] },
	{ name: "Synth Lead", instruments: [
		{ name: "Lead 1 (square)", id: 837 },
		{ name: "Lead 2 (sawtooth)", id: 846 },
		{ name: "Lead 3 (calliope)", id: 856 },
		{ name: "Lead 4 (chiff)", id: 868 },
		{ name: "Lead 5 (charang)", id: 878 },
		{ name: "Lead 6 (voice)", id: 892 },
		{ name: "Lead 7 (fifths)", id: 903 },
		{ name: "Lead 8 (bass + lead)", id: 913 },
	] },
	{ name: "Synth Pad", instruments: [
		{ name: "Pad 1 (new age)", id: 923 },
		{ name: "Pad 2 (warm)", id: 944 },
		{ name: "Pad 3 (polysynth)", id: 954 },
		{ name: "Pad 4 (choir)", id: 965 },
		{ name: "Pad 5 (bowed)", id: 976 },
		{ name: "Pad 6 (metallic)", id: 986 },
		{ name: "Pad 7 (halo)", id: 997 },
		{ name: "Pad 8 (sweep)", id: 1008 },
	] },
	{ name: "Synth Effects", instruments: [
		{ name: "FX 1 (rain)", id: 1017 },
		{ name: "FX 2 (soundtrack)", id: 1029 },
		{ name: "FX 3 (crystal)", id: 1039 },
		{ name: "FX 4 (atmosphere)", id: 1053 },
		{ name: "FX 5 (brightness)", id: 1069 },
		{ name: "FX 6 (goblins)", id: 1084 },
		{ name: "FX 7 (echoes)", id: 1095 },
		{ name: "FX 8 (sci-fi)", id: 1108 },
	] },
	{ name: "Ethnic", instruments: [
		{ name: "Sitar", id: 1120 },
		{ name: "Banjo", id: 1129 },
		{ name: "Shamisen", id: 1137 },
		{ name: "Koto", id: 1147 },
		{ name: "Kalimba", id: 1158 },
		{ name: "Bagpipe", id: 1166 },
		{ name: "Fiddle", id: 1174 },
		{ name: "Shanai", id: 1185 },
	] },
	{ name: "Percussive", instruments: [
		{ name: "Tinkle Bell", id: 1192 },
		{ name: "Agogo", id: 1200 },
		{ name: "Steel Drums", id: 1209 },
		{ name: "Woodblock", id: 1217 },
		{ name: "Taiko Drum", id: 1228 },
		{ name: "Melodic Tom", id: 1241 },
		{ name: "Synth Drum", id: 1252 },
		{ name: "Reverse Cymbal", id: 1262 },
	] },
	{ name: "Sound effects", instruments: [
		{ name: "Guitar Fret Noise", id: 1273 },
		{ name: "Breath Noise", id: 1283 },
		{ name: "Seashore", id: 1293 },
		{ name: "Bird Tweet", id: 1311 },
		{ name: "Telephone Ring", id: 1324 },
		{ name: "Helicopter", id: 1339 },
		{ name: "Applause", id: 1365 },
		{ name: "Gunshot", id: 1382 },
	] },
];

const INSTRUMENT_NAME_DICT: { [id: number]: string } = (() => {
	let ret: { [id: number]: string } = {};
	INSTRUMENTS.forEach((category) => {
		category.instruments.forEach((instrument) => {
			const { id, name } = instrument;
			ret[id] = name;
		})
	});
	return ret;
})();

export const lookupInstrumentName = (instrument: number) => {
	return INSTRUMENT_NAME_DICT[instrument] || `(instrument ${instrument})`;
};

export class InstrumentDialog extends React.Component<InstrumentDialogProps> {
	render() {
		const { musicInstrument, chordInstrument, onMusicInstrumentChange, onChordInstrumentChange, visible, onClose: handleClose } = this.props;

		return <div className={classnames("dialog", { hidden: !visible })}>
			<div className="dialog-inner">
			<table>
				<thead>
					<tr><th colSpan={2} /><th>Instrument</th></tr>
				</thead>
				<tbody>
					{INSTRUMENTS.map((category: InstrumentCategory, i: number) => <Fragment key={i}>
						<tr><th>Music</th><th>Chord</th><th>{category.name}</th></tr>
						{category.instruments.map((entry: InstrumentEntry) =>
							<tr key={entry.id}>
								<td><input type="radio" name="music-instrument" value={entry.id} checked={musicInstrument === entry.id} onChange={() => onMusicInstrumentChange(entry.id)} /></td>
								<td><input type="radio" name="chord-instrument" value={entry.id} checked={chordInstrument === entry.id} onChange={() => onChordInstrumentChange(entry.id)} /></td>
								<td>{entry.name}</td>
							</tr>
						)}
					</Fragment>)}
				</tbody>
			</table>
			</div>
			<button className="btn dialog-close" onClick={handleClose}>close</button>
		</div>;
	}
}

	

