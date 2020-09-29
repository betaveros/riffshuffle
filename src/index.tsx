import React, { Component, ChangeEvent, FileEvent, CSSProperties, Fragment } from "react";
import ReactDOM from "react-dom";
import MIDIFile from 'midifile';
import WebAudioFontPlayer from 'webaudiofont';
import MIDIEvents from 'midievents';
import debounce from 'lodash.debounce';

import allstar from './allstar.json';
import castle from './castle.json';
import happybirthday from './happybirthday.json';
import lifelight from './lifelight.json';
import lostinthoughts from './lostinthoughts.json';
import miichannel from './miichannel.json';
import twinkle from './twinkle.json';
import song1 from './song1.json';
import song2 from './song2.json';
import song3 from './song3.json';
import song4 from './song4.json';

import classnames from "classnames";

import { InstrumentDialog, DEFAULT_MUSIC_INSTRUMENT, DEFAULT_CHORD_INSTRUMENT, lookupInstrumentName } from './instruments.tsx';

const GM_ZERO_INDEXED_PERCUSSION_CHANNEL = 9;
const WEBSOCKET_URL = "ws://localhost:8765";
const CHORD_INCLUSION_TOLERANCE = 1.0e-6;

const INSTRUMENT = 0;

const PRESETS = {
	song1,
	song2,
	song3,
	song4,
	allstar,
	castle,
	happybirthday,
	lifelight,
	lostinthoughts,
	miichannel,
	twinkle,
};

// wrapper to handle making sounds, in theory??
class AudioWrapper {
	audioContext: any;
	player: any;

	constructor() {
		const AudioContextFunc = window.AudioContext || window.webkitAudioContext;
		this.audioContext = new AudioContextFunc();
		this.player = new WebAudioFontPlayer();
		this.loadInstrument(DEFAULT_MUSIC_INSTRUMENT);
		this.loadInstrument(DEFAULT_CHORD_INSTRUMENT);
	}

	loadInstrument(instrument: number) {
		console.log('loading', instrument);
		const info = this.player.loader.instrumentInfo(instrument);
		this.player.loader.startLoad(this.audioContext, info.url, info.variable);
		this.player.loader.waitLoad(() => {
			console.log('cached', info);
		});
	}

	play = ({ instrument, when, pitch, duration, volume }: { instrument: number, when: number, pitch: number, duration: number, volume: number }) => {
		if (volume) {
			const info = this.player.loader.instrumentInfo(instrument);
			try {
				return this.player.queueWaveTable(this.audioContext, this.audioContext.destination, window[info.variable], when, pitch, duration, volume); // can call .cancel() on the answer
			} catch (e) {
				// meh
				console.error(e);
			}
		}
	};

	currentTime() {
		return this.audioContext.currentTime;
	}
}

// extremely generic
type Chord = {
	name: string; // user-facing
	value: string; // machine-facing, for serialization/deserialization
	score: number; // 0 to 1
	midis: Array<number>;
};

type ChordDropdownProps = {
	value: Chord;
	suggestion?: Chord;
	locked: boolean;
	recommendations: Array<Chord>;
	sectionCount: number; // show n - 1 split buttonss
	onChangeLocked: (locked: boolean) => void;
	onChange: (chord: Chord, locked: boolean) => void;
	onDelete: () => void;
	onSplit: (i: number) => void;
	onEnter: () => void;
	onLeave: () => void;
	onAcceptSuggestion: () => void;
	onEnterSplit: (i: number) => void;
	onLeaveSplit: (i: number) => void;
	deleteDisabled: boolean;
	disabled: boolean;
	style: CSSProperties;
	isChanging: boolean;
};

const renderScore = (score: number): string => {
	return score === 1.0 ? "best" : `${(score * 100).toFixed(2)}%`;
};

class ChordDropdown extends React.Component<ChordDropdownProps> {
	constructor(props: ChordDropdownProps) {
		super(props);
	}

	handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
		const rawValue = event.target.value;
		if (rawValue === "unlocked") {
			this.props.onChange(this.props.recommendations[0], false);
		} else {
			let changed = false;
			for (let i = 0; i < this.props.recommendations.length; i++) {
				const chord = this.props.recommendations[i];
				if (chord.value === rawValue) {
					this.props.onChange(chord, true);
					changed = true;
				}
			}
			if (!changed) {
				console.error("dropdown got change event with unknown chord!?");
			}
		}
	};

	render() {
		const { style, locked, value, suggestion, recommendations, sectionCount, onChangeLocked, onDelete, onEnter, onLeave, onAcceptSuggestion, onSplit, onEnterSplit, onLeaveSplit, disabled, deleteDisabled, isChanging } = this.props;

		const scoreDisplay = renderScore(value.score);

		const className = classnames("chord-dropdown", { "is-changing": isChanging });

		return (
			<div style={style} className={className} onMouseEnter={onEnter} onMouseLeave={onLeave}>
				<div className="sections">
				<div />
				{
					[...Array(Math.max(sectionCount - 1, 0)).keys()].map((i) => (
						<button className="btn" key={i} onClick={() => onSplit(i)} onMouseEnter={() => onEnterSplit(i)} onMouseLeave={() => onLeaveSplit(i)}>split</button>
					))
				}
				{
					sectionCount <= 1 &&
						<button className="btn" disabled={true} style={{ visibility: "hidden" }}>split</button>
				}
				<div />
				</div>
				<button className="btn" onClick={onDelete} disabled={disabled || deleteDisabled}>&lt; merge</button>
				<div>{value.name}</div>
				<div className="score">{scoreDisplay}</div>
				{locked ? <div className="locked">locked</div> : <div className="unlocked">unlocked</div>}
				<button className="btn" onClick={() => onChangeLocked(!locked)} disabled={disabled}>{locked ? "unlock" : "lock"}</button>
				<button className="btn green" onClick={onAcceptSuggestion} disabled={disabled || !suggestion} title={suggestion ? "set to the suggested chord " + suggestion.name : locked ? "alternative chords are not suggested when locked" : "the current value of this chord is already the suggested chord"}>{suggestion ? `set to ${suggestion.name}` : "n/a"}</button>
			</div>
		);
	}
}

// A less flexible representation of a MIDI where every note has a start and a stop.
type PartialRigidNote = {
	channel: number;
	pitch: number;
	start: number;
	end?: number;
};
type RigidNote = {
	channel: number;
	pitch: number;
	start: number;
	end: number;
};
type RigidEvent = {
	noteIndex: number; // only makes sense in the context of that musical piece
	start: boolean;
	time: number;
};
type TimeSignature = {
	numerator: number;
	denominator: number;
};
type RigidMusic = {
	duration: number; // seconds
	notes: Array<RigidNote>;
	events: Array<RigidEvent>;
	timeSignature: TimeSignature;
	keySignature: number; // number of sharps or flats
	mode: "major" | "minor";
	tempoMicrosecondsPerQuarterNote: number;
};

const parseMidiFile = (midiFile): RigidMusic => {
	// const events = midiFile.getMidiEvents();
	const events = midiFile.getEvents();

	if(midiFile.header.getTimeDivision() === MIDIFile.Header.TICKS_PER_BEAT) {
		console.log(midiFile.header.getTicksPerBeat());
	} else {
		throw new Error("Don't understand MIDIs with SMPTE frames?");
		// midiFile.header.getSMPTEFrames();
		// midiFile.header.getTicksPerFrame();
	}

	let duration = 0;

	// indexed by (zero-indexed) channel
	let openNotes: Array<{ [pitch: number]: number|undefined /* noteIndex */ }> = Array(16).fill(1).map(() => ({}));
	let rigidNotes: Array<PartialRigidNote> = [];
	let rigidEvents: Array<RigidEvent> = [];

	// 4/4 is MIDI standard default
	let timeSignature: TimeSignature = {
		numerator: 4,
		denominator: 4,
	};
	let keySignature: number = 0; // number of sharps or flats
	let mode: "major" | "minor" = "major";
	let tempoMicrosecondsPerQuarterNote = 500000; // 120 bpm

	console.log(events);

	events.forEach((event) => {
		const playTime = event.playTime / 1000;
		duration = Math.max(duration, playTime);

		const channel = event.channel;
		if (event.type == MIDIEvents.EVENT_META) {
			if (event.subtype == MIDIEvents.EVENT_META_TIME_SIGNATURE) {
				console.warn("time signature", event);
				timeSignature.numerator = event.param1;
				timeSignature.denominator = Math.pow(2, event.param2);
			} else if (event.subtype == MIDIEvents.EVENT_META_SET_TEMPO) {
				console.warn("tempo", event);
				tempoMicrosecondsPerQuarterNote = event.tempo;
			} else if (event.subtype == MIDIEvents.EVENT_META_TRACK_NAME) {
				console.warn("track name", event);
			} else if (event.subtype == MIDIEvents.EVENT_META_KEY_SIGNATURE) {
				console.log("key signature", event);
				keySignature = event.key;
				if (keySignature > 128) { keySignature -= 256; }
				// event.key = number of sharps (theoretically negative for flats but instead it's a 8-bit unsigned integer)

				mode = event.scale ? "minor" : "major";
			} else {
				console.warn("unknown meta", event);
			}
		} else if (event.type === MIDIEvents.EVENT_MIDI) {
			if (event.subtype == MIDIEvents.EVENT_MIDI_NOTE_ON) {
				const pitch = event.param1;

				// elided check if (pitch >= 35 && pitch <= 81) if 9, [0, 127] else
				const openNoteIndex = openNotes[channel][pitch];
				if (openNoteIndex !== undefined) {
					rigidNotes[openNoteIndex].end = playTime;
					rigidEvents.push({
						noteIndex: openNoteIndex,
						start: false,
						time: playTime,
					});
					openNotes[channel][pitch] = undefined; // for clarity...
				}

				openNotes[channel][pitch] = rigidNotes.length;
				rigidEvents.push({
					noteIndex: rigidNotes.length,
					start: true,
					time: playTime,
				});
				rigidNotes.push({ channel, pitch, start: playTime });
			} else if (event.subtype === MIDIEvents.EVENT_MIDI_NOTE_OFF) {
				const pitch = event.param1;

				const openNoteIndex = openNotes[channel][pitch];
				if (openNoteIndex !== undefined) {
					rigidNotes[openNoteIndex].end = playTime;
					rigidEvents.push({
						noteIndex: openNoteIndex,
						start: false,
						time: playTime,
					});
					openNotes[channel][pitch] = undefined;
				} else {
					console.warn("turning off note not open", event);
				}
			} else if (event.subtype == MIDIEvents.EVENT_MIDI_PROGRAM_CHANGE) {
				// not handled
				console.warn('program change', event.channel, event);
			} else if (event.subtype === MIDIEvents.EVENT_MIDI_CONTROLLER) {
				// not handled
				console.warn('controller', event.channel, event);
			} else if (event.subtype == MIDIEvents.EVENT_MIDI_PITCH_BEND) {
				// not handled
				console.warn('bend', event.channel, event);
			} else {
				console.warn('unknown', event.channel, event);
			}
		} else {
			console.warn('unknown type', event);
		}
	});
	return {
		duration,
		notes: rigidNotes.map((note) => ({
			channel: note.channel,
			pitch: note.pitch,
			start: note.start,
			end: note.end === undefined ? note.start + 0.001 : note.end,
		})),
		events: rigidEvents,
		timeSignature,
		keySignature,
		mode,
		tempoMicrosecondsPerQuarterNote,
	};
};

const computeDefaultChordQuarterNoteLengths = (music: RigidMusic): Array<number> => {
	if (music.timeSignature.numerator % 3 === 0) {
		return [1, 2, 3, 6];
	} else {
		return [1, 2, 4];
	}
};
const computeDefaultChordLength = (music: RigidMusic): number => {
	const nls = computeDefaultChordQuarterNoteLengths(music);
	return nls[nls.length - 2] * music.tempoMicrosecondsPerQuarterNote / 1000000;
};

type ChordRec = {
	time: number;
	value: Chord;
	locked: boolean;
	recommendations: Array<Chord>;
	suggestion?: Chord;
};

type MusicPlayerState = {
	loading: boolean;
	outerLeft: number;
	audioTime: number;
	musicTime: number;
	isPlaying: boolean;
	music: RigidMusic|undefined;
	musicInstrument: number;
	chordInstrument: number;
	strumChords: boolean;
	musicVolume: number;
	chordVolume: number;
	defaultChordLength: number;
	chords: Array<ChordRec>;
	uiKeySignature: number;
	uiMode: "major" | "relative-minor" | "parallel-minor" | "mixed-relative" | "mixed-parallel";
	uiMinorness: number;
	uiJazz: number;
	uiFirstWeight: number;
	isRandom: boolean;
	uiChaos: number;
	seed: string;
	error: string|undefined;
	currentChangingChordIndex: number|undefined;
	isOtherChordDialogVisible: boolean;
	bottomBass: number;
	zoomIndex: number;
	showChords: boolean;
	showDebug: boolean;
	debugInfo: string;
	saveLoadTextarea: string;
	saveLoadError: string|undefined;
	isSaveLoadDialogVisible: boolean;
	isInstrumentDialogVisible: boolean;
	hoveredChord: number|undefined;
	hoveredSplit: number|undefined;
};

const FIFTHS_STRING = "FCGDAEB";

const getNoteByFifthsFromC = (fifths: number) => {
	const accidentalCount = Math.floor((fifths + 1) / 7);
	const indexInCycle = fifths + 1 - accidentalCount * 7;
	const accidentals = accidentalCount < 0 ? '♭'.repeat(-accidentalCount) : '♯'.repeat(accidentalCount);
	return FIFTHS_STRING[indexInCycle] + accidentals;
};

const getNoteRepresentation = (absoluteSemitone: number, keySignature: number) => {
	const majorTonic = keySignature * 7;
	const relativeSemitone = absoluteSemitone - majorTonic;

	// I think we want to use Ab to C#, and then corresponding ones for other notes
	// Note that 7 is self-inverse mod 12, but clamp it down to -4

	const circleOfFifthsPosition = ((relativeSemitone * 7 + 4) % 12 + 12) % 12 - 4;

	return getNoteByFifthsFromC(keySignature + circleOfFifthsPosition);
};

// 0 = C-1
const getNoteRepresentationWithOctave = (absoluteSemitone: number, keySignature: number) => {
	const repr = getNoteRepresentation(absoluteSemitone, keySignature);
	let octave = Math.floor(absoluteSemitone / 12) - 1;
	if (repr === 'C♭') octave++;
	return repr + octave;
};

const cMajor: Chord = { name: "C",  score: 1, value: "C", midis: [48, 48 + 4, 48 + 7] };
const fMajor: Chord = { name: "F",  score: 1, value: "F", midis: [53, 53 + 4, 53 + 7] };
const gMajor: Chord = { name: "G",  score: 1, value: "G", midis: [55, 55 + 4, 55 + 7] };
const aMinor: Chord = { name: "Am", score: 1, value: "Am", midis: [45, 45 + 3, 45 + 7] };

const JAZZ_MAGNITUDE = 100;
const FIRST_WEIGHT_MAX = 100;
const MINORNESS_MAX = 100;
const CHAOS_MAGNITUDE = 100;
const DEFAULT_VOLUME = 50;
const MAX_VOLUME = 100;

// in percent
const ZOOM_LIST = [10, 15, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 500, 800, 1000];
const DEFAULT_ZOOM_INDEX = ZOOM_LIST.indexOf(100);

const defaultRec: ChordRec = {
	time: 0,
	value: cMajor,
	locked: false,
	recommendations: [cMajor, fMajor, gMajor, aMinor],
};

class MusicPlayer extends Component<{}, MusicPlayerState> {
	audioWrapper: AudioWrapper|undefined = undefined;
	startAudioTime = 0;
	lastAudioTime: number|undefined = undefined;
	openNotes: { [pitch: number]: { cancel: () => void }|undefined } = {};
	wsReady = false;
	ws: WebSocket;
	seq = 0; // sequence number for websocket stuff

	constructor(props: {}) {
		super(props);

		this.state = {
			loading: false,
			outerLeft: 0,
			audioTime: 0,
			musicTime: 0,
			isPlaying: false,
			music: undefined,
			musicInstrument: DEFAULT_MUSIC_INSTRUMENT,
			chordInstrument: DEFAULT_CHORD_INSTRUMENT,
			strumChords: true,
			musicVolume: DEFAULT_VOLUME,
			chordVolume: DEFAULT_VOLUME,
			defaultChordLength: 1,
			chords: [
				{ ...defaultRec, time: 0 },
				{ ...defaultRec, time: 1 },
				{ ...defaultRec, time: 2 },
				{ ...defaultRec, time: 3 },
				{ ...defaultRec, time: 4 },
				{ ...defaultRec, time: 5 },
				{ ...defaultRec, time: 6 },
				{ ...defaultRec, time: 7 },
			],
			uiKeySignature: 0,
			uiMode: "major",
			uiMinorness: 50,
			uiJazz: 0,
			uiFirstWeight: 0,
			isRandom: false,
			uiChaos: 0,
			seed: "",
			error: undefined,
			currentChangingChordIndex: undefined,
			isOtherChordDialogVisible: false,
			bottomBass: 48,
			zoomIndex: DEFAULT_ZOOM_INDEX,
			showChords: true,
			showDebug: false,
			debugInfo: "",
			saveLoadTextarea: "",
			saveLoadError: undefined,
			isSaveLoadDialogVisible: false,
			isInstrumentDialogVisible: false,
			hoveredChord: undefined,
			hoveredSplit: undefined,
		};

		this.displayRef = React.createRef();
		this.displayOuterRef = React.createRef();

		const ws = new WebSocket(WEBSOCKET_URL);
		this.ws = ws;
		ws.onopen = () => {
			this.wsReady = true;
		};
		ws.onclose = event => {
			console.error("Connection closed: " + JSON.stringify(event));
			this.setState({ error: "Connection closed" });
		};
		ws.onerror = event => {
			console.error("Connection error: " + JSON.stringify(event));
			this.setState({ error: "Connection error" });
		};
		ws.onmessage = event => {
			console.log("websocket said:");
			console.log(event.data);
			const data = JSON.parse(event.data);
			const stateDiff = {};
			if (data.error) {
				this.setState({ error: data.error });
			}
			if (data.allChords) { stateDiff.allChords = data.allChords; }
			if (data.result) { stateDiff.chords = data.result; }
			if (data.seq === this.seq) {
				stateDiff.loading = false;
				this.setState(stateDiff);
			}
		};
	}

	togglePlaying = () => {
		if (!this.state.music) return;

		if (!this.audioWrapper) {
			throw new Error("togglePlaying: audioWrapper not defined");
		}
		if (this.state.isPlaying) {
			this.setState({
				isPlaying: false,
				musicTime: this.clampTime(this.audioWrapper.currentTime() - this.startAudioTime),
			});
		} else {
			this.setState({ isPlaying: true });
			// from start: this.startAudioTime = this.audioWrapper.currentTime();
			this.startAudioTime = this.audioWrapper.currentTime() - this.state.musicTime;
			this.lastAudioTime = undefined;
			this.cancelOpenNotes();
			this.tickBody(true);
		}
	};

	resetPlaying = () => this.setPlayPosition(0);

	componentDidMount() {
		this.audioWrapper = new AudioWrapper();
		window.setTimeout(this.tick, 250);
	}

	playTestInstrument = () => {
		if (this.audioWrapper) {
			this.audioWrapper.play({
				instrument: INSTRUMENT,
				when: 0,
				pitch: 60,
				duration: 3.5,
				volume: 0.5,
			});
		}
	};

	cancelOpenNotes = () => {
		for (let pitch in this.openNotes) {
			const openNote = this.openNotes[pitch];
			if (openNote) {
				openNote.cancel();
				this.openNotes[pitch] = undefined;
			}
		}
	};

	getMaxTime = () => {
		const { music, defaultChordLength } = this.state;

		let maxTime = 0;
		if (music) {
			maxTime = Math.ceil(music.duration / defaultChordLength) * defaultChordLength;
		}

		return maxTime;
	};

	clampTime = (t: number): number => {
		return Math.max(0, Math.min(this.getMaxTime(), t));
	};

	tickBody = (isPlaying: boolean) => {
		const { music, chords, musicInstrument, chordInstrument, musicVolume, chordVolume, defaultChordLength, strumChords } = this.state;
		const { audioWrapper } = this;

		if (!audioWrapper) {
			throw new Error("tickBody: no audioWrapper defined");
		}

		const currentAudioTime = audioWrapper.currentTime();

		if (music && isPlaying) {
			// which notes/events do we schedule?
			const lowerAudioTime = this.lastAudioTime === undefined ? currentAudioTime : this.lastAudioTime + 0.5;
			const upperAudioTime = currentAudioTime + 0.5;

			chords.forEach((rec, i) => {
				const firstPlayAudioTime = this.startAudioTime + rec.time;
				const secondsPerQuarterNote = music.tempoMicrosecondsPerQuarterNote / 1000000;
				const endTime = this.startAudioTime + (i + 1 < chords.length ? chords[i + 1].time : Math.ceil(music.duration / defaultChordLength) * defaultChordLength);
				let isFirst = true;
				for (let playAudioTime = firstPlayAudioTime; playAudioTime + 1.0e-6 < endTime; playAudioTime += secondsPerQuarterNote) {
					if (lowerAudioTime <= playAudioTime && playAudioTime < upperAudioTime) {
						rec.value.midis.forEach((pitch, i) => {
							const volume = chordVolume / MAX_VOLUME * (isFirst ? 1 : (i === 0 ? 0.5 : 0.25));
							audioWrapper.play({
								instrument: chordInstrument,
								when: playAudioTime,
								pitch: pitch,
								duration: (i === 0 ? endTime - firstPlayAudioTime : secondsPerQuarterNote),
								volume,
							});
						});
					}
					if (!strumChords) break;
					isFirst = false;
				}
			});

			if (music) {
				music.events.forEach((event) => {
					const playAudioTime = this.startAudioTime + event.time;

					if (lowerAudioTime <= playAudioTime && playAudioTime < upperAudioTime) {
						const note = music.notes[event.noteIndex];

						if (event.start) {
							if (note.channel === GM_ZERO_INDEXED_PERCUSSION_CHANNEL) {
								// nope
							} else {
								// if (event.param1 >= 0 && event.param1 <= 127)
								// console.log(event);
								this.openNotes[note.pitch] = audioWrapper.play({
									instrument: musicInstrument,
									when: playAudioTime,
									pitch: note.pitch,
									duration: note.end - note.start,
									volume: musicVolume / MAX_VOLUME,
								});
							}
						} else {
							const openNote = this.openNotes[note.pitch];
							if (openNote) {
								// openNote.cancel();
								this.openNotes[note.pitch] = undefined;
							}
						}
					}
				});
			}
		}

		this.lastAudioTime = currentAudioTime;

		if (this.state.isPlaying) {
			if (currentAudioTime - this.startAudioTime > this.getMaxTime()) {
				this.setState({
					musicTime: 0,
					isPlaying: false,
				});
			} else {
				this.setState({
					musicTime: this.clampTime(currentAudioTime - this.startAudioTime),
				});
			}
		}
		this.setState({
			audioTime: currentAudioTime,
		});
	};

	tick = () => {
		this.tickBody(this.state.isPlaying);

		window.setTimeout(this.tick, 250);
	};

	handleKeyDown = (event) => {
		console.log(event);
		if (event.key === " ") {
			this.togglePlaying();
			event.preventDefault();
		}
	};

	handleMusicInstrumentChange = (instrument: number) => {
		this.setState({ musicInstrument: instrument });

		if (!this.audioWrapper) {
			throw new Error("music instrument change: audioWrapper not defined");
		}

		this.audioWrapper.loadInstrument(instrument);
	};

	handleChordInstrumentChange = (instrument: number) => {
		this.setState({ chordInstrument: instrument });

		if (!this.audioWrapper) {
			throw new Error("chord instrument change: audioWrapper not defined");
		}

		this.audioWrapper.loadInstrument(instrument);
	};

	handleMusicVolumeChange = (event: ChangeEvent<HTMLInputElement>) => {
		const volume = Number(event.target.value);

		if (0 <= volume && volume <= 100) {
			this.setState({ musicVolume: volume });
		}
	};

	handleChordVolumeChange = (event: ChangeEvent<HTMLInputElement>) => {
		const volume = Number(event.target.value);

		if (0 <= volume && volume <= 100) {
			this.setState({ chordVolume: volume });
		}
	};

	sendWSWithPreserve = debounce((preserve) => {
		if (this.wsReady && this.state.music) {
			this.seq++;
			this.setState({ loading: true });
			this.ws.send(JSON.stringify({
				seq: this.seq,
				music: this.state.music,
				mode: this.state.uiMode,
				keySignature: this.state.uiKeySignature,
				minorness: this.state.uiMinorness / MINORNESS_MAX,
				chordLength: this.state.defaultChordLength,
				constraints: this.state.chords.map((rec) => ({ 'time': rec.time, 'value': rec.value.value, 'locked': rec.locked })),
				jazziness: this.state.uiJazz / JAZZ_MAGNITUDE,
				firstWeight: Math.exp(this.state.uiFirstWeight / FIRST_WEIGHT_MAX * 8),
				determinismWeight: Math.pow(1 - this.state.uiChaos / CHAOS_MAGNITUDE, 3), // interpolate 0 -> 1 -> 8
				seed: this.state.isRandom && this.state.seed ? this.state.seed : null,
				bottomBass: this.state.bottomBass,
				tolerance: CHORD_INCLUSION_TOLERANCE,
				preserve,
			}));
		}
	}, 50);

	sendWS = () => this.sendWSWithPreserve(false);
	sendWSPreserve = () => this.sendWSWithPreserve(true);

	handleUiJazzChange = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ uiJazz: Number(event.target.value) }, this.sendWS);
	};

	handleUiFirstWeightChange = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ uiFirstWeight: Number(event.target.value) }, this.sendWS);
	};

	handleUiChaosChange = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ uiChaos: Number(event.target.value) }, this.sendWS);
	};

	handleClickChordQuarterNoteLength = (qs: number) => {
		if (this.state.chords.every((chord) => !chord.locked) || window.confirm("This will reset all chord lengths and locked chords. Do you wish to continue?")) {
			this.setState((state) => ({ defaultChordLength: qs * state.music.tempoMicrosecondsPerQuarterNote / 1000000, chords: [] }), this.sendWS);
		}
	};

	handleChangeIsRandom = (event: ChangeEvent<HTMLInputElement>) => {
		if (event.target.checked) {
			this.setState(state => ({
				isRandom: true,
				seed: state.seed || Math.floor(Math.random() * 3656158440062976).toString(36),
			}), this.sendWS);
		} else {
			this.setState({ isRandom: false }, this.sendWS);
		}
	};

	handleSeedChange = (event: ChangeEvent<HTMLInputElement>) => {
		console.log('seed change');
		this.setState({ seed: event.target.value }, this.sendWS);
	};
	handleSeedRandomize = () => {
		// rather silly string generation
		const randomString = Math.floor(Math.random() * 3656158440062976).toString(36);
		this.setState({ seed: randomString }, this.sendWS);
	};

	setPlayPosition = (t: number) => {
		t = this.clampTime(t);

		if (this.state.isPlaying) {
			if (!this.audioWrapper) throw new Error("setPlayPosition: no audioWrapper defined");

			this.startAudioTime = this.audioWrapper.currentTime() - t;
			this.lastAudioTime = undefined;
			this.cancelOpenNotes();
			this.tickBody(true);
		} else {
			this.setState({ musicTime: t });
		}
	};

	getPixelsPerTime = () => {
		return ZOOM_LIST[this.state.zoomIndex];
	};

	handleClickDisplay = (event) => {
		this.setPlayPosition((event.clientX - this.displayRef.current.getBoundingClientRect().left) / this.getPixelsPerTime());
	};

	handleSharpenKeySignature = () => this.setState((state) => ({
		uiKeySignature: Math.min(state.uiKeySignature + 1, 7),
	}), this.sendWS);
	handleFlattenKeySignature = () => this.setState((state) => ({
		uiKeySignature: Math.max(state.uiKeySignature - 1, -7),
	}), this.sendWS);

	handleFileSelect = (event: FileEvent) => {
		const file = event.target.files[0];
		const fileReader = new FileReader();
		fileReader.onload = (progressEvent) => {
			// console.log("loading");
			// console.log(progressEvent);
			const { target } = progressEvent;
			if (target) {
				if (!this.audioWrapper) {
					throw new Error("handleFileSelect/onload: audioWrapper not defined");
				}
				const arrayBuffer = target.result;
				const midiFile = new MIDIFile(arrayBuffer);
				const music = parseMidiFile(midiFile);
				const chordLength = computeDefaultChordLength(music);
				this.startAudioTime = this.audioWrapper.currentTime();
				this.setState({
					music,
					chords: [],
					uiKeySignature: music.keySignature === "minor" ? "relative-minor" : "major",
					uiMode: music.mode,
					defaultChordLength: chordLength,
					debugInfo: JSON.stringify(music),
				}, this.sendWS);
			}
		};
		fileReader.readAsArrayBuffer(file);
	};

	handleSetMajorMode = () => { this.setState({ uiMode: "major" }, this.sendWS); };
	handleSetRelativeMinorMode = () => { this.setState({ uiMode: "relative-minor" }, this.sendWS); };
	handleSetParallelMinorMode = () => { this.setState({ uiMode: "parallel-minor" }, this.sendWS); };
	handleSetMixedRelativeMode = () => { this.setState({ uiMode: "mixed-relative" }, this.sendWS); };
	handleSetMixedParallelMode = () => { this.setState({ uiMode: "mixed-parallel" }, this.sendWS); };

	handleUiMinornessChange = (event) => {
		this.setState({ uiMinorness: event.target.value }, this.sendWS);
	};

	renderRandomControls() {
		const { seed, isRandom, uiChaos } = this.state;

		return (
			<div className="random-controls" style={{ visibility: isRandom ? "visible" : "hidden" }}>
			<input type="text" onChange={this.handleSeedChange} value={seed} />
			<button className="btn" onClick={this.handleSeedRandomize}>rerandomize</button>
			<div title="Higher values make the system more likely to pick random chords; at maximum value, all chords are completely random. Lower values increase the chances of the most likely chords.">
			<div className="range-label">
				<div>Chaos</div>
				<div>(−100 to 100)</div>
			</div>
			<input type="number" min={-CHAOS_MAGNITUDE} max={CHAOS_MAGNITUDE} value={uiChaos} onChange={this.handleUiChaosChange} className="ui-parameter" />
			</div>
			</div>
		);
	};

	changeChord = (i: number, newChord: Chord, lock: boolean) => {
		this.setState((oldState) => {
			const newChords: Array<ChordRec> = [
				...oldState.chords.slice(0, i),
				{
					time: oldState.chords[i].time,
					value: newChord,
					locked: lock,
					recommendations: oldState.chords[i].recommendations,
					suggestion: oldState.chords[i].suggestion && oldState.chords[i].suggestion.value !== oldState.chords[i].value.value ? oldState.chords[i].suggestion : undefined,
				},
				...oldState.chords.slice(i+1, oldState.chords.length),
			];

			return { ...oldState, chords: newChords };
		}, this.sendWSPreserve);
	};

	handleAcceptAllSuggestions = () => {
		this.setState((oldState) => (
			{
				...oldState,
				chords: oldState.chords.map((chord) =>
					chord.locked ? chord : {
						...chord,
						value: chord.suggestion || chord.value,
						suggestion: undefined,
					}
				),
			}
		), this.sendWSPreserve);
	};

	modifyZoom = (delta: number) => {
		this.setState((state) => ({
			...state,
			zoomIndex: Math.max(0, Math.min(ZOOM_LIST.length - 1, state.zoomIndex + delta)),
		}));
	};

	modifyBottomBass = (delta: number) => {
		this.setState((state) => ({
			...state,
			bottomBass: Math.max(0, Math.min(116, state.bottomBass + delta)),
		}), this.sendWSPreserve);
	};

	handleChangeShowChords = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ showChords: event.target.checked });
	};

	handleChangeShowDebug = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ showDebug: event.target.checked });
	};

	handleChangeStrumChords = (event: ChangeEvent<HTMLInputElement>) => {
		this.setState({ strumChords: event.target.checked });
	};

	handleShowOtherChordDialog = () => { this.setState({ isOtherChordDialogVisible: true }); }
	handleHideOtherChordDialog = () => { this.setState({ isOtherChordDialogVisible: false }); }

	renderChordChangeInterface() {
		const { chords, currentChangingChordIndex } = this.state;
		if (currentChangingChordIndex === undefined || currentChangingChordIndex >= chords.length) {
			return null;
		}

		const chord = chords[currentChangingChordIndex];

		const { locked, recommendations, value } = chord;

		const defaultChord = locked ? recommendations[0] : value;

		let chordChoices = [
			{ chord: defaultChord, locked: false, disabled: !locked },
			...chord.recommendations.map(chord => ({ chord, locked: true, disabled: locked && value.value === chord.value })),
		];

		return <div className="chord-change-wrap"><table className="chord-change" style={{ marginLeft: chord.time * this.getPixelsPerTime() }}>
			<thead>
			<tr>
			<th></th><th>chord</th><th>score</th>
			</tr>
			</thead>
			<tbody>
			{
				chordChoices.map(({ chord, locked, disabled }, i) =>
					<tr key={i}>
					<td>
						<button className="btn" onClick={() => this.changeChord(currentChangingChordIndex, chord, locked)} disabled={disabled}>choose</button>
					</td>
					<td>{chord.name}</td>
					<td className="change-score">{renderScore(chord.score)}</td>
					<td className="change-locked">{locked && "lock"}</td>
					</tr>
				)
			}
			<tr><td colSpan={4}><button className="btn" onClick={this.handleShowOtherChordDialog}>other...</button></td></tr>
			</tbody>
		</table></div>;
	}

	handleOuterScroll = () => {
		this.setState({
			outerLeft: this.displayOuterRef.current.scrollLeft,
		});
	};

	renderMusicDisplay() {
		const semitoneHeight = 14;
		const { loading, chords, music, defaultChordLength, currentChangingChordIndex, showChords, hoveredChord, hoveredSplit, uiKeySignature } = this.state;

		const pixelsPerTime = this.getPixelsPerTime();

		let minPitch = 120;
		let maxPitch = 0;

		const maxTime = this.getMaxTime();

		if (showChords) {
			chords.forEach((rec) => {
				rec.value.midis.forEach((midi) => {
					minPitch = Math.min(minPitch, midi);
					maxPitch = Math.max(maxPitch, midi);
				});
			});
		}

		if (music) {
			music.notes.forEach((note) => {
				minPitch = Math.min(minPitch, note.pitch);
				maxPitch = Math.max(maxPitch, note.pitch);
			});
		}

		const displayHeight = semitoneHeight * Math.max(maxPitch - minPitch + 3, 0);

		const hasSuggestions = chords.some(chord => chord.suggestion);

		return <div className={classnames("music-display-outer", { loading })} style={{minHeight: displayHeight + 160}} ref={this.displayOuterRef} onScroll={this.handleOuterScroll}>
			<div className="music-display" style={{height: displayHeight, width: maxTime * pixelsPerTime}} onClick={this.handleClickDisplay} ref={this.displayRef}>
			{
				loading && <div className="loading-text">loading...</div>
			}
			{
				chords.map((rec, i) => {
					let duration = defaultChordLength;
					if (i + 1 < chords.length) duration = chords[i + 1].time - rec.time;
					else if (music) duration = Math.ceil(music.duration / defaultChordLength) * defaultChordLength - rec.time;

					return <Fragment key={i}>
					{
						showChords && rec.value.midis.map((midi, j) => {
							const style = {
								top: (maxPitch + 1 - midi) * semitoneHeight,
								left: rec.time * pixelsPerTime,
								width: duration * pixelsPerTime,
								height: semitoneHeight,
							};
							// console.log(style);
							return <div className="chord-note" key={`chord-${i}-${j}`} style={style} />;
						})
					}
					<div className="chord-barline" style={{ left: rec.time * pixelsPerTime, }} />
					</Fragment>;
				})
			}
			{
				music &&
				music.notes.map((note, i) => {
					const style = {
						top: (maxPitch + 1 - note.pitch) * semitoneHeight, // ???
						left: note.start * pixelsPerTime,
						width: (note.end - note.start) * pixelsPerTime,
						height: semitoneHeight,
					};
					const noteRepr = getNoteRepresentationWithOctave(note.pitch, uiKeySignature);

					// bounds checks because song changing can leave bad states
					const hovered = (hoveredChord !== undefined && 0 <= hoveredChord && hoveredChord < chords.length && chords[hoveredChord].time - CHORD_INCLUSION_TOLERANCE <= note.start && (hoveredChord === chords.length - 1 || note.start < chords[hoveredChord + 1].time - CHORD_INCLUSION_TOLERANCE));

					// console.log(style);
					return <div className={classnames("note", { hovered })} key={i} style={style}>{noteRepr}</div>;
				})
			}
				<div className="now-bar" style={{ left: this.state.musicTime * pixelsPerTime }}/>
			{
				hoveredSplit !== undefined &&
				<div className="hovered-split" style={{ left: hoveredSplit * pixelsPerTime, }}/>
			}
			</div>
			<div className="chords-display">
			{
				chords.map((rec, i) => {
					let duration = defaultChordLength;
					if (i + 1 < chords.length) duration = chords[i + 1].time - rec.time;
					else if (music) duration = Math.ceil(music.duration / defaultChordLength) * defaultChordLength - rec.time;

					const width = duration * pixelsPerTime;

					let sectionCount = 1;
					if (music) {
						const secondsPerQuarterNote = music.tempoMicrosecondsPerQuarterNote / 1000000;
						sectionCount = Math.round(duration / secondsPerQuarterNote);
					}

					return <ChordDropdown
						key={i}
						value={rec.value}
						suggestion={rec.suggestion}
						locked={rec.locked}
						recommendations={rec.recommendations}
						isChanging={i === currentChangingChordIndex}
						disabled={!music}
						deleteDisabled={i === 0}
						sectionCount={sectionCount}
						onChangeLocked={(locked: boolean) => this.changeChord(i, rec.value, locked)}
						onDelete={() => {
							this.setState((oldState) => {
								const newChords = [
									...oldState.chords.slice(0, i),
									...oldState.chords.slice(i+1, oldState.chords.length),
								];

								return { ...oldState, chords: newChords };
							}, this.sendWSPreserve);
						}}
						onEnter={() => this.setState({ hoveredChord: i })}
						onLeave={() => this.setState({ hoveredChord: undefined })}
						onAcceptSuggestion={() => this.changeChord(i, rec.suggestion, false)}
						onSplit={(pos) => {
							this.setState((oldState) => {
								const oldChord = oldState.chords[i];
								const oldChordTime = oldChord.time;
								const nextChordTime = i + 1 < oldState.chords.length ? oldState.chords[i + 1].time : Math.ceil(music.duration / defaultChordLength) * defaultChordLength;
								const newChordTime = oldChordTime + (nextChordTime - oldChordTime) * (pos + 1) / sectionCount;

								const newChords = [
									...oldState.chords.slice(0, i+1),
									{
										...oldChord,
										time: newChordTime,
									},
									...oldState.chords.slice(i+1, oldState.chords.length),
								];

								return { ...oldState, chords: newChords, hoveredSplit: undefined };
							}, this.sendWSPreserve);
						}}
						onEnterSplit={(pos) => {
							this.setState((oldState) => {
								const oldChord = oldState.chords[i];
								const oldChordTime = oldChord.time;
								const nextChordTime = i + 1 < oldState.chords.length ? oldState.chords[i + 1].time : Math.ceil(music.duration / defaultChordLength) * defaultChordLength;
								const newChordTime = oldChordTime + (nextChordTime - oldChordTime) * (pos + 1) / sectionCount;

								return { ...oldState, hoveredSplit: newChordTime };
							});
						}}
						onLeaveSplit={(pos) => this.setState({ hoveredSplit: undefined })}
						style={{ width: width, }}
					/>;
				})
			}
			</div>
			<button className="btn green fixed-full-width" onClick={this.handleAcceptAllSuggestions} disabled={!hasSuggestions} style={{ marginLeft: this.state.outerLeft }}>
			accept all suggestions
			</button>
			<div className="change-display">
			{
				chords.map((rec, i) => {
					let duration = defaultChordLength;
					if (i + 1 < chords.length) duration = chords[i + 1].time - rec.time;
					else if (music) duration = Math.ceil(music.duration / defaultChordLength) * defaultChordLength - rec.time;

					const width = duration * pixelsPerTime;
					return <div className="start-change" style={{width}}><button className="btn" onClick={() => {
						this.setState((oldState) => ({
							...oldState,
							currentChangingChordIndex:
								i === oldState.currentChangingChordIndex
									? undefined
									: i,
						}));
					}}
					disabled={!music}>change</button></div>;
				})
			}
			</div>
			{this.renderChordChangeInterface()}
		</div>;
	}

	renderMusicPlayerBody() {
		const { music, isRandom, audioTime, musicTime, bottomBass, showChords, showDebug, debugInfo, musicInstrument, chordInstrument, strumChords, uiKeySignature } = this.state;
		// console.log('random', isRandom);

		const zoom = this.getPixelsPerTime();

		const bottomBassDisplay = getNoteRepresentationWithOctave(bottomBass, uiKeySignature);
		const topBassDisplay = getNoteRepresentationWithOctave(bottomBass + 11, uiKeySignature);
		const zoomDisplay = `${zoom}%`;

		return <Fragment>
			<div className="parameter-bar">
			{this.renderKeySignature()}
			<div className="box vertical-box">
				<div>Reset all chords to length:</div>
				<div className="chord-reset">
					{music && computeDefaultChordQuarterNoteLengths(music).map((qs, i) =>
						<button key={i} className="btn" onClick={() => this.handleClickChordQuarterNoteLength(qs)}>{qs}</button>
					)}
				</div>
			</div>
			<div className="box" title="Higher values increase the importance of coherence between melody and chord. Lower values increase the importance of chord transitions.">
				<div className="range-label">
					<div>"Jazziness"</div>
					<div>(−100 to 100)</div>
				</div>
				<input type="number" min={-JAZZ_MAGNITUDE} max={JAZZ_MAGNITUDE} value={this.state.uiJazz} onChange={this.handleUiJazzChange} className="ui-parameter" disabled={!music} />
			</div>
			<div className="box">
				<span title="Higher values increase the influence of the first note in each measure on its chord.">
				First note emphasis:{" "}
				<input type="number" min={0} max={FIRST_WEIGHT_MAX} value={this.state.uiFirstWeight} onChange={this.handleUiFirstWeightChange} className="ui-parameter" disabled={!music} />
				</span>
			</div>
			<div className="box">
				<label>
				<input type="checkbox" checked={isRandom} onChange={this.handleChangeIsRandom} /> randomize?{" "}
				</label>
				{this.renderRandomControls()}
			</div>
			</div>
			<div className="play-bar">
			<div className="box">
				<div className="music-time">{musicTime.toFixed(2)}</div>
				<button className="btn" onClick={this.togglePlaying} disabled={!music} title="(or Spacebar) ">{this.state.isPlaying ? "Stop" : "Play"}</button>
				<button className="btn" onClick={this.resetPlaying} disabled={!music}>Reset</button>
			</div>
			<div className="box">
			<div className="instrument-display">
				<div>
					Music
				</div>
				<div>
					<label>Volume
					<input type="number" min="0" max={MAX_VOLUME} value={this.state.musicVolume} onChange={this.handleMusicVolumeChange} className="ui-parameter" disabled={!music} />
					</label>
				</div>
				<div>{lookupInstrumentName(musicInstrument)}</div>
				<div />
				<div>
					Chords
				</div>
				<div>
					<label>Volume
					<input type="number" min="0" max={MAX_VOLUME} value={this.state.chordVolume} onChange={this.handleChordVolumeChange} className="ui-parameter" disabled={!music} />
					</label>
				</div>
				<div>{lookupInstrumentName(chordInstrument)}</div>
				<div><label><input type="checkbox" checked={strumChords} onChange={this.handleChangeStrumChords} /> strum?</label></div>
			</div>
			<button onClick={this.handleShowInstrumentDialog}>change instruments</button>
			</div>
			</div>
			<div>
				Zoom:{" "}
				<button className="btn" onClick={() => this.modifyZoom(-1)}>−</button>
				<span className="zoom">{zoomDisplay}</span>
				<button className="btn" onClick={() => this.modifyZoom(+1)}>+</button>
				{" "}
				Bass:
				{" "}
				<button className="btn" onClick={() => this.modifyBottomBass(-12)}>−8va</button>
				<button className="btn" onClick={() => this.modifyBottomBass(-1)}>−1</button>
				<span className="bottom-bass">{bottomBassDisplay} to {topBassDisplay}</span>
				<button className="btn" onClick={() => this.modifyBottomBass(+1)}>+1</button>
				<button className="btn" onClick={() => this.modifyBottomBass(+12)}>+8va</button>
				<label>
				<input type="checkbox" checked={showChords} onChange={this.handleChangeShowChords} /> show chord notes?
				</label>
			</div>
			{this.renderMusicDisplay()}
			<div className="debug">
				{
					showDebug &&
					<Fragment>
						<textarea readOnly={true} value={debugInfo} />
						{audioTime.toFixed(2)}
						<button className="btn" onClick={this.playTestInstrument}>Test</button>
					</Fragment>
				}
				<label>
				<input type="checkbox" checked={showDebug} onChange={this.handleChangeShowDebug} /> debug
				</label>
			</div>
		</Fragment>;
	}

	renderKeySignature() {
		const { uiKeySignature, uiMode, uiMinorness } = this.state;

		let display = '0♮';
		if (uiKeySignature > 0) {
			display = `${uiKeySignature}♯`;
		} else if (uiKeySignature < 0) {
			display = `${-uiKeySignature}♭`;
		}

		const majorTonic = getNoteByFifthsFromC(uiKeySignature);
		const minorTonic = getNoteByFifthsFromC(uiKeySignature + 3);

		return <div className="key-signature-box box">
			<div className="title">Key signature:</div>
			<div className="adjust">
			<button className="btn" onClick={this.handleFlattenKeySignature} disabled={uiKeySignature <= -7}>♭</button>
			<span className="key-signature">{display}</span>
			<button className="btn" onClick={this.handleSharpenKeySignature} disabled={uiKeySignature >= 7}>♯</button>
			</div>

			<label className="major"><input type="radio" name="mode" value="major" checked={uiMode === "major"} onChange={this.handleSetMajorMode} />{majorTonic} major</label>
			<label className="relative-minor"><input type="radio" name="mode" value="relative-minor" checked={uiMode === "relative-minor"} onChange={this.handleSetRelativeMinorMode} />{minorTonic} minor</label>
			<label className="parallel-minor"><input type="radio" name="mode" value="parallel-minor" checked={uiMode === "parallel-minor"} onChange={this.handleSetParallelMinorMode} />{majorTonic} minor</label>
			<label className="mixed-relative"><input type="radio" name="mode" value="mixed-relative" checked={uiMode === "mixed-relative"} onChange={this.handleSetMixedRelativeMode} />{MINORNESS_MAX-uiMinorness}% {majorTonic} major, {uiMinorness}% {minorTonic} minor</label>
			<label className="mixed-parallel"><input type="radio" name="mode" value="mixed-parallel" checked={uiMode === "mixed-parallel"} onChange={this.handleSetMixedParallelMode} />{MINORNESS_MAX-uiMinorness}% {majorTonic} major, {uiMinorness}% {majorTonic} minor</label>
			<div className="minorness">
			(Minor: <input type="number" min={0} max={MINORNESS_MAX} value={uiMinorness} onChange={this.handleUiMinornessChange} className="ui-parameter" />%)
			</div>
		</div>;
	}

	renderError() {
		if (this.state.error !== undefined) {
			return <div className='error'>{this.state.error}</div>;
		}
		return null;
	}

	renderOtherChordDialog() {
		const { currentChangingChordIndex, chords, allChords, isOtherChordDialogVisible } = this.state;

		let tbody = null;
		if (currentChangingChordIndex !== undefined && currentChangingChordIndex < chords.length) {
			const currentChord = chords[currentChangingChordIndex];

			let scoreLookup: { [chordValue: string]: number } = {};
			currentChord.recommendations.forEach((chord: Chord) => {
				scoreLookup[chord.value] = chord.score;
			});

			tbody = <tbody>
				{allChords.map((chord: Chord) => {
					const disabled = currentChord.locked && currentChord.value.value === chord.value;
					const score = (chord.value in scoreLookup) ? renderScore(scoreLookup[chord.value]) : "—";
					return <tr>
						<td>
							<button className="btn" onClick={() => this.changeChord(currentChangingChordIndex, chord, true)} disabled={disabled}>choose</button>
						</td>
						<td>{chord.name}</td>
						<td>{score}</td>
					</tr>;
				})}
			</tbody>;
		}

		return <div className={classnames("dialog", "other-chord-dialog", { hidden: !isOtherChordDialogVisible || currentChangingChordIndex === undefined })}>
			<div className="dialog-inner">
				<table>
					<thead>
						<tr><th /><th>Chord</th><th>Score</th></tr>
					</thead>
					{tbody}
				</table>
			</div>
			<button className="btn dialog-close" onClick={this.handleHideOtherChordDialog}>close</button>
		</div>;
	}

	handleChangePreset = (event) => {
		const music = PRESETS[event.target.value];
		const chordLength = computeDefaultChordLength(music);

		this.startAudioTime = this.audioWrapper.currentTime();
		this.setState({
			music,
			chords: [],
			defaultChordLength: chordLength,
			uiKeySignature: music.keySignature,
			uiMode: music.mode,
			debugInfo: JSON.stringify(music),
		}, this.sendWS);
	};

	handleShowInstrumentDialog = () => {
		this.setState({ isInstrumentDialogVisible: true });
	};

	handleHideInstrumentDialog = () => {
		this.setState({ isInstrumentDialogVisible: false });
	};

	handleSaveLoadTextareaChange = (event) => {
		this.setState({ saveLoadTextarea: event.target.value });
	};

	generateSaveText = () => {
		const { music, musicInstrument, chordInstrument, strumChords, musicVolume, chordVolume, defaultChordLength, chords, uiKeySignature, uiMode, uiMinorness, uiJazz, uiFirstWeight, isRandom, uiChaos, seed, bottomBass, showChords } = this.state;

		if (music) {
			return JSON.stringify({
				version: 1,
				music, musicInstrument, chordInstrument, strumChords, musicVolume, chordVolume, defaultChordLength, chords, uiKeySignature, uiMode, uiMinorness, uiJazz, uiFirstWeight, isRandom, uiChaos, seed, bottomBass, showChords,
			});
		}

		return "";
	};

	handleShowSaveLoadDialog = () => {
		const text = this.generateSaveText();

		this.setState({
			isSaveLoadDialogVisible: true,
			saveLoadTextarea: text,
		});
	};

	handleHideSaveLoadDialog = () => {
		this.setState({ isSaveLoadDialogVisible: false });
	};

	handleLoadTextarea = () => {
		try {
			const { version, music, musicInstrument, chordInstrument, strumChords, musicVolume, chordVolume, defaultChordLength, chords, uiKeySignature, uiMode, uiMinorness, uiJazz, uiFirstWeight, isRandom, uiChaos, seed, bottomBass, showChords } = JSON.parse(this.state.saveLoadTextarea);
			this.setState({ version, music, musicInstrument, chordInstrument, strumChords, musicVolume, chordVolume, defaultChordLength, chords, uiKeySignature, uiMode, uiMinorness, uiJazz, uiFirstWeight, isRandom, uiChaos, seed, bottomBass, showChords });

			this.audioWrapper.loadInstrument(musicInstrument);
			this.audioWrapper.loadInstrument(chordInstrument);
		} catch (exc) {
			this.setState({ saveLoadError: String(exc) });
		}
	};

	// black magic
	handleDownload = () => {
		const blob = new Blob([this.generateSaveText()], { type: "text/plain;charset=utf-8" });
		const a = document.createElement("a"), url = URL.createObjectURL(blob);
		a.href = url;
		a.download = `riffshuffle-${new Date().toISOString().replace(/[^-a-zA-Z0-9]/g,'')}.txt`;
		document.body.appendChild(a);
		a.click();
		setTimeout(function() {
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);
		}, 0);
	};

	render() {
		const { chordInstrument, musicInstrument, music } = this.state;
		return <div className="App" onKeyDown={this.handleKeyDown} tabIndex={-1}>
			{this.renderError()}
			<div className="box">
				<select onChange={this.handleChangePreset} value="">
					<option value="">choose a preset...</option>
					{
						Object.keys(PRESETS).map((key) => <option key={key} value={key}>{key}</option>)
					}
				</select>
				{" or upload a MIDI file: "}
				<input type="file" onChange={this.handleFileSelect} />
				{" or "}
				<button className="btn" onClick={this.handleShowSaveLoadDialog}>save/load</button>
			</div>
			{this.renderMusicPlayerBody()}
			<div className={classnames("dialog", "save-load-dialog", { hidden: !this.state.isSaveLoadDialogVisible })}>
				<div className="dialog-inner">
					<p>Copy the text below somewhere to save your work, or change it and click Load, or <button className="btn" onClick={this.handleDownload} disabled={!music}>download</button> your work as a text file.</p>
					<textarea value={this.state.saveLoadTextarea} onChange={this.handleSaveLoadTextareaChange} />
					<button className="btn" onClick={this.handleLoadTextarea}>Load</button>
					{
						this.state.saveLoadError &&
						<div className='error'>{this.state.saveLoadError}</div>
					}
				</div>
				<button className="btn dialog-close" onClick={this.handleHideSaveLoadDialog}>close</button>
			</div>
			<InstrumentDialog
				chordInstrument={chordInstrument}
				musicInstrument={musicInstrument}
				onMusicInstrumentChange={this.handleMusicInstrumentChange}
				onChordInstrumentChange={this.handleChordInstrumentChange}
				visible={this.state.isInstrumentDialogVisible}
				onClose={this.handleHideInstrumentDialog}
			/>
			{this.renderOtherChordDialog()}
		</div>;
	}
}

ReactDOM.render(<MusicPlayer />, document.getElementById("root"));
