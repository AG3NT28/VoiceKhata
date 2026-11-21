import React, { useCallback, useEffect, useRef, useState } from 'react';
import { getState, sendAudio, sendText, undoLast, speakText } from './services/api';
import { VoiceRecorder, isRecordingSupported, speak, stopSpeaking } from './services/audio';

const INTENT_META = {
  ADD_CREDIT: { label: 'Udhaar', tone: 'bg-rose-100 text-rose-700 ring-rose-200' },
  RECORD_PAYMENT: { label: 'Payment', tone: 'bg-emerald-100 text-emerald-700 ring-emerald-200' },
  CHECK_BALANCE: { label: 'Balance', tone: 'bg-sky-100 text-sky-700 ring-sky-200' },
  DAILY_SUMMARY: { label: 'Summary', tone: 'bg-violet-100 text-violet-700 ring-violet-200' },
  ADD_CUSTOMER: { label: 'New customer', tone: 'bg-amber-100 text-amber-700 ring-amber-200' },
  CORRECT_LAST: { label: 'Correction', tone: 'bg-orange-100 text-orange-700 ring-orange-200' },
  CLARIFY: { label: 'Clarify', tone: 'bg-slate-200 text-slate-700 ring-slate-300' },
};

const EXAMPLES = [
  'Ramesh ka 340 rupaye udhaar likho',
  'Suresh ne 500 rupaye diye',
  'Ramesh ka kitna baaki hai',
  'aaj ka summary',
];

const money = (paise) =>
  `₹${(Number(paise || 0) / 100).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export default function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [online, setOnline] = useState(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [ttsOn, setTtsOn] = useState(true);
  const [typed, setTyped] = useState('');
  const [processingMs, setProcessingMs] = useState(null);
  const [language, setLanguage] = useState('hi-IN,en-IN');

  const recorderRef = useRef(null);
  const resultRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getState();
      setSnapshot(data);
      setOnline(true);
    } catch (err) {
      setOnline(false);
      setError((prev) => prev || `Backend se connect nahi hua: ${err.message}`);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!recording) return undefined;
    const id = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(id);
  }, [recording]);

  const run = async (promise) => {
    const data = await promise;
    setResult(data);
    if (data.reply_text && ttsOn) {
      let played = false;
      try {
        await Promise.race([
          speakText(data.reply_text, 'hi-en').then(() => { played = true; }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('tts timeout')), 4000)),
        ]);
      } catch {
        /* fall through to browser TTS */
      }
      if (!played) speak(data.reply_text);
    }
    await refresh();
    setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 50);
  };

  const toggleRecording = async () => {
    if (busy) return;

    if (!recording) {
      setError('');
      setResult(null);
      stopSpeaking();
      try {
        recorderRef.current = new VoiceRecorder();
        await recorderRef.current.start();
        setSeconds(0);
        setRecording(true);
      } catch (err) {
        setError(`Microphone permission chahiye: ${err.message}`);
      }
      return;
    }

    setRecording(false);
    setBusy(true);
    const startedAt = Date.now();
    try {
      const wav = await recorderRef.current?.stop();
      if (!wav) throw new Error('Koi audio capture nahi hua, dobara try karein.');
      await run(sendAudio(wav, language));
      setProcessingMs(Date.now() - startedAt);
    } catch (err) {
      setError(err.message);
      setProcessingMs(null);
    } finally {
      recorderRef.current = null;
      setBusy(false);
    }
  };

  const submitTyped = async (event) => {
    event.preventDefault();
    const text = typed.trim();
    if (!text || busy) return;
    setError('');
    setBusy(true);
    stopSpeaking();
    try {
      await run(sendText(text));
      setTyped('');
      setProcessingMs(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const summary = snapshot?.summary;
  const customers = snapshot?.customers || [];
  const recent = snapshot?.recent || [];
  const activeCustomerId = result?.customer?.id;
  const intentMeta = result ? INTENT_META[result.intent] || INTENT_META.CLARIFY : null;
  const stt = result?.stt;

  return (
    <div className="min-h-screen bg-[#fbf7f0] text-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-500 text-xl shadow-sm shadow-amber-200">
              🎙️
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight sm:text-2xl">Voice Khata</h1>
              <p className="text-sm text-slate-500">
                {snapshot?.shop?.name || 'Kirana store voice ledger'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setTtsOn((value) => !value);
                if (ttsOn) stopSpeaking();
              }}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold ring-1 transition ${
                ttsOn
                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                  : 'bg-white text-slate-500 ring-slate-200'
              }`}
            >
              {ttsOn ? '🔊 Voice reply on' : '🔇 Voice reply off'}
            </button>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 outline-none focus:border-amber-400"
            >
              <option value="hi-IN,en-IN">Hindi + English</option>
              <option value="indic-auto">Auto-detect</option>
              <option value="hi-IN">Hindi only</option>
              <option value="te-IN,en-IN">Telugu + English</option>
              <option value="kn-IN,en-IN">Kannada + English</option>
              <option value="ta-IN,en-IN">Tamil + English</option>
              <option value="en-IN">English only</option>
            </select>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ${
                online
                  ? 'bg-white text-emerald-700 ring-emerald-200'
                  : 'bg-white text-rose-600 ring-rose-200'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  online ? 'bg-emerald-500' : 'bg-rose-500'
                }`}
              />
              {online === null ? 'Connecting' : online ? 'Backend live' : 'Offline'}
            </span>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            {/* ---------------- microphone ---------------- */}
            <section className="rounded-3xl border border-amber-100 bg-white p-6 shadow-sm shadow-amber-100/60 sm:p-8">
              <div className="flex flex-col items-center text-center">
                <div className="relative flex h-36 w-36 items-center justify-center">
                  {recording && (
                    <>
                      <span className="absolute h-32 w-32 animate-ping rounded-full bg-rose-300/50" />
                      <span className="absolute h-24 w-24 animate-pulse rounded-full bg-rose-200/70" />
                    </>
                  )}
                  <button
                    type="button"
                    onClick={toggleRecording}
                    disabled={busy || !isRecordingSupported()}
                    className={`relative z-10 flex h-24 w-24 items-center justify-center rounded-full text-4xl text-white shadow-lg transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 ${
                      recording
                        ? 'bg-rose-500 shadow-rose-200'
                        : 'bg-amber-500 shadow-amber-200 hover:bg-amber-600'
                    }`}
                    aria-label={recording ? 'Stop recording' : 'Start recording'}
                  >
                    {recording ? '■' : '🎤'}
                  </button>
                </div>

                <p className="mt-4 text-base font-semibold">
                  {recording
                    ? `Sun raha hoon. ${seconds}s (max 8s)`
                    : busy
                    ? 'Process ho raha hai…'
                    : 'Bolne ke liye dabaiye'}
                </p>
                <p className="mt-1 max-w-md text-sm text-slate-500">
                  {recording
                    ? 'Kaam khatam hone par dobara dabaiye. Hindi, English ya Hinglish chalega.'
                    : 'Jaise: "Ramesh ka 340 rupaye udhaar likho" ya "Suresh ne 500 rupaye diye".'}
                </p>

                {!isRecordingSupported() && (
                  <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700">
                    Is browser me microphone support nahi hai. Neeche text se try karein.
                  </p>
                )}
              </div>

              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setTyped(example)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition hover:border-amber-300 hover:text-amber-700"
                  >
                    {example}
                  </button>
                ))}
              </div>

              <form onSubmit={submitTyped} className="mt-5 flex gap-2">
                <input
                  value={typed}
                  onChange={(event) => setTyped(event.target.value)}
                  placeholder="Ya yahan likhiye…"
                  className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-amber-400 focus:bg-white"
                />
                <button
                  type="submit"
                  disabled={busy || !typed.trim()}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-40"
                >
                  Bhejein
                </button>
              </form>

              {error && (
                <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-100">
                  {error}
                </p>
              )}
            </section>

            {/* ---------------- result ---------------- */}
            {result && (
              <section
                ref={resultRef}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${intentMeta.tone}`}
                  >
                    {intentMeta.label}
                  </span>
                  <span className="text-xs text-slate-400">
                    confidence {Math.round((result.confidence || 0) * 100)}%
                  </span>
                  {stt?.engine && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-500">
                      {stt.engine}
                    </span>
                  )}
                  {stt?.latency != null && (
                    <span className="text-[11px] text-slate-400">
                      STT {Math.round(stt.latency * 1000)} ms
                    </span>
                  )}
                  {processingMs != null && (
                    <span className="text-[11px] font-semibold text-emerald-600">
                      Total {(processingMs / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>

                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Aapne kaha
                </p>
                <p className="mt-1 text-lg font-medium leading-snug">
                  {result.transcript || <span className="text-slate-400">(kuch nahi suna)</span>}
                </p>
                {result.transcript && (
                  <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Suna gaya: {result.transcript.split(/\s+/).length} words · {stt?.model || 'prisma-v3.0'}
                  </div>
                )}

                <div className="mt-4 rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-100">
                  <div className="flex items-start gap-3">
                    <span className="text-lg">🗣️</span>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                        Jawab
                      </p>
                      <p className="mt-1 text-base font-medium text-amber-900">
                        {result.reply_text}
                      </p>
                      {ttsOn && (
                        <button
                          type="button"
                          onClick={async () => {
                            let played = false;
                            try {
                              await Promise.race([
                                speakText(result.reply_text, 'hi-en').then(() => { played = true; }),
                                new Promise((_, reject) => setTimeout(() => reject(new Error('tts timeout')), 4000)),
                              ]);
                            } catch {}
                            if (!played) speak(result.reply_text);
                          }}
                          className="mt-2 text-xs font-semibold text-amber-700 underline decoration-amber-300 underline-offset-2"
                        >
                          Dobara sunein
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={busy}
                        onClick={async () => {
                          setError('');
                          setBusy(true);
                          stopSpeaking();
                          try {
                            const data = await undoLast();
                            setResult((prev) => ({ ...prev, reply_text: data.reply_text }));
                            await refresh();
                          } catch (err) {
                            setError(err.message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                        className="mt-2 ml-3 text-xs font-semibold text-rose-600 underline decoration-rose-300 underline-offset-2 disabled:opacity-40"
                      >
                        Undo last entry
                      </button>
                    </div>
                  </div>
                </div>

                {result.customer && (
                  <div className="mt-4 flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
                    <div>
                      <p className="text-sm font-semibold">{result.customer.name}</p>
                      <p className="text-xs text-slate-500">Code {result.customer.code}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-500">Baaki</p>
                      <p className="text-lg font-bold text-slate-900">
                        {money(result.customer.balance_paise)}
                      </p>
                    </div>
                  </div>
                )}

                {result.options?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {result.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setTyped(`${option} ka kitna baaki hai`)}
                        className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-amber-300"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* ---------------- recent ---------------- */}
            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                  Recent entries
                </h2>
                <span className="text-xs text-slate-400">{recent.length} shown</span>
              </div>
              {recent.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-400">
                  Abhi koi entry nahi. Mic dabakar shuru karein.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {recent.map((item) => (
                    <li key={item.id} className="flex items-center justify-between py-2.5">
                      <div className="flex items-center gap-3">
                        <span
                          className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${
                            item.type === 'credit'
                              ? 'bg-rose-50 text-rose-600'
                              : 'bg-emerald-50 text-emerald-600'
                          }`}
                        >
                          {item.type === 'credit' ? '↑' : '↓'}
                        </span>
                        <div>
                          <p className="text-sm font-medium">{item.customer}</p>
                          <p className="text-xs text-slate-400">
                            {item.type === 'credit' ? 'Udhaar' : 'Payment'}
                            {item.status !== 'active' && ` · ${item.status}`}
                          </p>
                        </div>
                      </div>
                      <span
                        className={`text-sm font-semibold ${
                          item.type === 'credit' ? 'text-rose-600' : 'text-emerald-600'
                        }`}
                      >
                        {item.type === 'credit' ? '+' : '−'}
                        {money(Math.round(item.amount_rupees * 100))}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* ---------------- right column ---------------- */}
          <div className="space-y-6">
            <section className="rounded-3xl bg-slate-900 p-6 text-white shadow-lg shadow-slate-300/40">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-400">
                Aaj ka hisaab
              </h2>
              <div className="mt-4 space-y-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-slate-300">Udhaar diya</span>
                  <span className="text-xl font-bold text-rose-300">
                    {money(summary?.total_credit_paise)}
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-slate-300">Jama hua</span>
                  <span className="text-xl font-bold text-emerald-300">
                    {money(summary?.total_payment_paise)}
                  </span>
                </div>
                <div className="h-px bg-white/10" />
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-slate-300">Net</span>
                  <span className="text-2xl font-extrabold">
                    {money(summary?.net_paise)}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {summary?.transaction_count || 0} entries · {summary?.date || '—'}
                </p>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                  Customers
                </h2>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
                  {customers.length}
                </span>
              </div>
              <ul className="space-y-2">
                {customers.map((customer) => (
                  <li
                    key={customer.id}
                    className={`flex items-center justify-between rounded-2xl px-3 py-2.5 ring-1 transition ${
                      customer.id === activeCustomerId
                        ? 'bg-amber-50 ring-amber-200'
                        : 'bg-slate-50 ring-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-xs font-bold text-slate-600 ring-1 ring-slate-200">
                        {customer.name.slice(0, 1).toUpperCase()}
                      </span>
                      <div>
                        <p className="text-sm font-semibold">{customer.name}</p>
                        <p className="text-[11px] text-slate-400">{customer.code}</p>
                      </div>
                    </div>
                    <span
                      className={`text-sm font-bold ${
                        customer.balance_paise > 0 ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {money(customer.balance_paise)}
                    </span>
                  </li>
                ))}
                {customers.length === 0 && (
                  <li className="py-6 text-center text-sm text-slate-400">Koi customer nahi</li>
                )}
              </ul>
            </section>

            <section className="rounded-3xl border border-dashed border-slate-300 bg-white/60 p-5">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-400">
                Pipeline
              </h2>
              <ol className="mt-3 space-y-2 text-xs text-slate-500">
                <li>1. Mic → 16 kHz WAV in browser</li>
                <li>2. Gnani Prisma v3 → Hinglish transcript</li>
                <li>3. LLM / rule parser → structured intent</li>
                <li>4. Ledger → paise-safe, idempotent entry</li>
                <li>5. Reply text → voice + UI update</li>
              </ol>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
