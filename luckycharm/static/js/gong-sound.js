// Synthesize gong sound using Web Audio API

function createGongSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    // Create oscillators for a metallic gong sound
    const fundamentalFreq = 130; // Low C
    const duration = 2.5;

    // Main tone
    const osc1 = audioContext.createOscillator();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(fundamentalFreq, audioContext.currentTime);

    // Harmonics
    const osc2 = audioContext.createOscillator();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(fundamentalFreq * 2.1, audioContext.currentTime);

    const osc3 = audioContext.createOscillator();
    osc3.type = 'sine';
    osc3.frequency.setValueAtTime(fundamentalFreq * 3.3, audioContext.currentTime);

    // Metallic overtone
    const osc4 = audioContext.createOscillator();
    osc4.type = 'triangle';
    osc4.frequency.setValueAtTime(fundamentalFreq * 5.7, audioContext.currentTime);

    // Create gain nodes for volume control
    const gain1 = audioContext.createGain();
    const gain2 = audioContext.createGain();
    const gain3 = audioContext.createGain();
    const gain4 = audioContext.createGain();
    const masterGain = audioContext.createGain();

    // Attack-decay envelope for gong strike
    const now = audioContext.currentTime;

    // Main tone - loud initial strike, slow decay
    gain1.gain.setValueAtTime(0, now);
    gain1.gain.linearRampToValueAtTime(0.4, now + 0.01);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + duration);

    // First harmonic - quick attack, medium decay
    gain2.gain.setValueAtTime(0, now);
    gain2.gain.linearRampToValueAtTime(0.15, now + 0.02);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + duration * 0.8);

    // Second harmonic - delayed, adds shimmer
    gain3.gain.setValueAtTime(0, now);
    gain3.gain.linearRampToValueAtTime(0.08, now + 0.05);
    gain3.gain.exponentialRampToValueAtTime(0.001, now + duration * 0.6);

    // High overtone - metallic ping
    gain4.gain.setValueAtTime(0, now);
    gain4.gain.linearRampToValueAtTime(0.05, now + 0.001);
    gain4.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    // Master volume
    masterGain.gain.setValueAtTime(0.6, now);

    // Connect nodes
    osc1.connect(gain1);
    osc2.connect(gain2);
    osc3.connect(gain3);
    osc4.connect(gain4);

    gain1.connect(masterGain);
    gain2.connect(masterGain);
    gain3.connect(masterGain);
    gain4.connect(masterGain);

    masterGain.connect(audioContext.destination);

    // Start oscillators
    osc1.start(now);
    osc2.start(now);
    osc3.start(now);
    osc4.start(now);

    // Stop oscillators after duration
    osc1.stop(now + duration);
    osc2.stop(now + duration * 0.8);
    osc3.stop(now + duration * 0.6);
    osc4.stop(now + 0.3);

    return audioContext;
}

// Export function
window.playGongSound = createGongSound;
