'use client';

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import { FileAudio } from 'lucide-react';
import { api, getErrorMessage } from '@/lib/api';
import { cn, formatDuration } from '@/lib/utils';
import { Card, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/feedback';
import type { Transcription } from '@/types';

/**
 * Transcripción con el audio de la llamada reproduciéndose en paralelo.
 *
 * El audio no se puede enlazar directamente: `audio_url` es una ruta interna del
 * almacenamiento y el endpoint exige el token JWT, que una etiqueta <audio> no
 * puede enviar. Por eso se descarga como blob y se reproduce desde un object URL,
 * igual que ya se hace con el reporte PDF.
 *
 * Expone `jumpToSegment(i)` para que la evidencia de cada nota lleve al momento
 * exacto de la llamada: resalta el segmento y, si el audio está listo, lo reproduce.
 */
export interface TranscriptPlayerHandle {
  jumpToSegment: (index: number) => void;
}

export const TranscriptPlayer = forwardRef<
  TranscriptPlayerHandle,
  {
    callId: number;
    transcription: Transcription;
    audioFilename?: string | null;
  }
>(function TranscriptPlayer({ callId, transcription, audioFilename }, ref) {
  const cardRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const activeRef = useRef<HTMLButtonElement | null>(null);
  const segmentRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [current, setCurrent] = useState(0);
  // Segmento al que se saltó desde la evidencia: se marca aunque no haya audio.
  const [focused, setFocused] = useState<number | null>(null);

  const segments = transcription.segments ?? [];

  useImperativeHandle(ref, () => ({
    jumpToSegment(index: number) {
      const seg = segments[index];
      if (!seg) return;
      setFocused(index);
      cardRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
      segmentRefs.current[index]?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
      seekTo(seg.start);
    },
  }));

  // Descarga del audio. El object URL se libera al desmontar o al cambiar de llamada.
  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    async function load() {
      try {
        const res = await api.get(`/calls/${callId}/audio`, {
          responseType: 'blob',
        });
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data as Blob);
        setAudioUrl(objectUrl);
      } catch (error) {
        if (!cancelled) setAudioError(getErrorMessage(error));
      }
    }
    load();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [callId]);

  // Segmento que suena ahora. -1 si el audio no ha empezado o está en un silencio.
  const activeIndex = segments.findIndex(
    (seg) => current >= seg.start && current < seg.end,
  );

  // Sigue al segmento activo dentro del scroll de la transcripción, sin arrastrar
  // la página entera.
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [activeIndex]);

  function seekTo(seconds: number) {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = seconds;
    void audio.play();
  }

  return (
    <div ref={cardRef} className="scroll-mt-4">
      <Card>
        <CardTitle className="mb-3">Transcripción</CardTitle>

        <div className="mb-3 flex items-center gap-2 text-small text-text-muted">
          <FileAudio size={14} />
          {audioFilename ?? 'audio'}
        </div>

        {/* Reproductor */}
        <div className="mb-4">
          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              preload="metadata"
              className="w-full"
              onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
            />
          ) : audioError ? (
            <p className="rounded-control bg-bg-accent px-3 py-2 text-small text-text-secondary">
              {audioError}
            </p>
          ) : (
            <p className="flex items-center gap-2 text-small text-text-muted">
              <Spinner className="h-4 w-4" />
              Cargando el audio…
            </p>
          )}
        </div>

        {/* Transcripción sincronizada */}
        <div className="flex max-h-96 flex-col gap-1 overflow-y-auto">
          {segments.length > 0 ? (
            segments.map((seg, i) => {
              const active = i === activeIndex;
              return (
                <button
                  key={i}
                  ref={(el) => {
                    segmentRefs.current[i] = el;
                    if (active) activeRef.current = el;
                  }}
                  type="button"
                  onClick={() => {
                    setFocused(null);
                    seekTo(seg.start);
                  }}
                  disabled={!audioUrl}
                  title={audioUrl ? 'Saltar a este momento' : undefined}
                  className={cn(
                    'flex gap-3 rounded-control px-2 py-1.5 text-left transition-colors',
                    active ? 'bg-rust-soft' : 'hover:bg-bg-accent',
                    i === focused && !active && 'bg-gold-soft',
                    audioUrl ? 'cursor-pointer' : 'cursor-default',
                  )}
                >
                  <span className="w-12 shrink-0 font-mono text-small text-text-muted">
                    {formatDuration(seg.start)}
                  </span>
                  <span
                    className={
                      seg.speaker === 'agent'
                        ? 'shrink-0 text-small font-semibold text-accent-primary'
                        : 'shrink-0 text-small font-semibold text-info'
                    }
                  >
                    {seg.speaker === 'agent' ? 'Ejecutivo' : 'Cliente'}:
                  </span>
                  <span className="text-small text-text-secondary">{seg.text}</span>
                </button>
              );
            })
          ) : (
            <p className="text-small text-text-secondary">
              {transcription.full_text}
            </p>
          )}
        </div>
      </Card>
    </div>
  );
});
