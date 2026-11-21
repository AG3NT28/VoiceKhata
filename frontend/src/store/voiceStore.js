import { create } from 'zustand';

/**
 * Centralized voice-khata state. App.jsx can migrate to this incrementally;
 * for now it's available for new components.
 */
export const useVoiceStore = create((set, get) => ({
  snapshot: null,
  result: null,
  recording: false,
  busy: false,
  error: '',
  ttsOn: true,
  language: 'hi-IN,en-IN',
  micLevel: 0,
  processingMs: null,

  setSnapshot: (snapshot) => set({ snapshot }),
  setResult: (result) => set({ result }),
  setRecording: (recording) => set({ recording }),
  setBusy: (busy) => set({ busy }),
  setError: (error) => set({ error }),
  setTtsOn: (ttsOn) => set({ ttsOn }),
  setLanguage: (language) => set({ language }),
  setMicLevel: (micLevel) => set({ micLevel }),
  setProcessingMs: (processingMs) => set({ processingMs }),

  refresh: async (getState) => {
    try {
      const data = await getState();
      set({ snapshot: data, error: '' });
    } catch (err) {
      set({ error: `Backend se connect nahi hua: ${err.message}` });
    }
  },
}));
