// auto-submit.swift — Apple-native hands-free "submit" for walk-and-talk.
//
// Presses Return (submit) without touching the keyboard. Apple frameworks only —
// no third-party, no Automator, no Shortcuts.
//
//   --button  Becomes the system "now playing" app (MediaPlayer framework) and
//             handles the Bluetooth/earbud PLAY-PAUSE as togglePlayPause → presses
//             Return. A TAP on your earbuds submits. NOTE: while running it owns
//             the media controls (your earbud tap won't control YouTube/Music
//             until you stop it) — intended for a focused walk-and-talk session.
//
//   --voice   End-of-utterance detector: AVAudioEngine taps the mic; after you
//             speak then go quiet for --hangover-ms, presses Return. Tune hangover
//             ABOVE Voice Control's typing lag.
//
//   --both    (default) both.
//
// Only ever presses Return (key code 36). Ctrl-C to stop.
// Permissions: Accessibility (the key press). --voice also needs Microphone.

import AVFoundation
import CoreGraphics
import Foundation
import MediaPlayer

// ---- options ----
var thresholdDb = -40.0, hangoverMs = 1500.0, minSpeechMs = 400.0, cooldownMs = 800.0
var useVoice = true, useButton = true
do {
    var it = CommandLine.arguments.dropFirst().makeIterator()
    func num(_ d: Double) -> Double { Double(it.next() ?? "") ?? d }
    while let a = it.next() {
        switch a {
        case "--voice":  useVoice = true;  useButton = false
        case "--button": useButton = true; useVoice = false
        case "--both":   useVoice = true;  useButton = true
        case "--threshold-db":  thresholdDb = num(thresholdDb)
        case "--hangover-ms":   hangoverMs = num(hangoverMs)
        case "--min-speech-ms": minSpeechMs = num(minSpeechMs)
        case "--cooldown-ms":   cooldownMs = num(cooldownMs)
        case "-h", "--help":
            print("usage: auto-submit [--button|--voice|--both] [--threshold-db N] [--hangover-ms N] [--min-speech-ms N] [--cooldown-ms N]")
            exit(0)
        default:
            FileHandle.standardError.write("ignoring unknown arg: \(a)\n".data(using: .utf8)!)
        }
    }
}

func err(_ s: String) { FileHandle.standardError.write((s + "\n").data(using: .utf8)!) }

// ---- the one action: press Return (cooldown so we never double-fire) ----
var lastFire = Date.distantPast
func pressReturn(_ why: String) {
    let now = Date()
    if now.timeIntervalSince(lastFire) * 1000.0 < cooldownMs { return }
    lastFire = now
    let src = CGEventSource(stateID: .hidSystemState)
    CGEvent(keyboardEventSource: src, virtualKey: 0x24, keyDown: true)?.post(tap: .cghidEventTap)   // 0x24 = Return
    CGEvent(keyboardEventSource: src, virtualKey: 0x24, keyDown: false)?.post(tap: .cghidEventTap)
    err("↩ submitted (\(why))")
}

// ---- --button: own "now playing", map earbud play/pause → Return ----
let silentEngine = AVAudioEngine()
let silentPlayer = AVAudioPlayerNode()
func startButton() {
    // claim the now-playing session by playing continuous silence
    if let fmt = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2),
       let buf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: 44100) {
        buf.frameLength = 44100  // zero-filled = silence
        silentEngine.attach(silentPlayer)
        silentEngine.connect(silentPlayer, to: silentEngine.mainMixerNode, format: fmt)
        do {
            try silentEngine.start()
            silentPlayer.scheduleBuffer(buf, at: nil, options: .loops, completionHandler: nil)
            silentPlayer.play()
        } catch { err("note: silent audio didn't start (\(error)); commands may still register") }
    }
    MPNowPlayingInfoCenter.default().nowPlayingInfo = [
        MPMediaItemPropertyTitle: "walk-and-talk",
        MPNowPlayingInfoPropertyPlaybackRate: 1.0,
    ]
    MPNowPlayingInfoCenter.default().playbackState = .playing

    let cc = MPRemoteCommandCenter.shared()
    let handler: (MPRemoteCommandEvent) -> MPRemoteCommandHandlerStatus = { _ in
        pressReturn("button"); return .success
    }
    for cmd in [cc.togglePlayPauseCommand, cc.playCommand, cc.pauseCommand] {
        cmd.isEnabled = true
        cmd.addTarget(handler: handler)
    }
    err("• button: tap your earbud play-pause to submit (walk-and-talk owns media controls while running)")
}

// ---- --voice: press Return after speech then silence ----
let micEngine = AVAudioEngine()
func startVoice() {
    let input = micEngine.inputNode
    let fmt = input.inputFormat(forBus: 0)
    if fmt.sampleRate == 0 { err("✗ no mic input — grant Microphone permission."); return }
    var speaking = false, speechMs = 0.0, silenceMs = 0.0
    input.installTap(onBus: 0, bufferSize: 2048, format: fmt) { buf, _ in
        guard let ch = buf.floatChannelData?[0] else { return }
        let n = Int(buf.frameLength); if n == 0 { return }
        var sum = 0.0
        for i in 0..<n { let s = Double(ch[i]); sum += s * s }
        let db = 20.0 * log10(max((sum / Double(n)).squareRoot(), 1e-9))
        let ms = Double(n) / fmt.sampleRate * 1000.0
        if db > thresholdDb {
            speaking = true; speechMs += ms; silenceMs = 0
        } else if speaking {
            silenceMs += ms
            if speechMs >= minSpeechMs && silenceMs >= hangoverMs {
                pressReturn("voice"); speaking = false; speechMs = 0; silenceMs = 0
            }
        }
    }
    do { try micEngine.start(); err("• voice: stop talking for \(Int(hangoverMs))ms to submit") }
    catch { err("✗ mic start failed: \(error) — grant Microphone permission.") }
}

// ---- run ----
if useButton { startButton() }
if useVoice { startVoice() }
if !useButton && !useVoice { err("nothing enabled"); exit(1) }
err("auto-submit running — only ever presses Return. Ctrl-C to stop.")
CFRunLoopRun()
