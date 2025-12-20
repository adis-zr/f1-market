import { cn } from '@/lib/utils';
import type { ReplayRace } from '@/api/types';

interface RaceTimelineProps {
  races: ReplayRace[];
  currentRace: number;
  onRaceSelect?: (raceNumber: number) => void;
}

export function RaceTimeline({ races, currentRace, onRaceSelect }: RaceTimelineProps) {
  return (
    <div className="w-full overflow-x-auto pb-2">
      <div className="flex items-center gap-1 min-w-max px-2">
        {races.map((race) => {
          const isCurrent = race.race_number === currentRace;
          const isCompleted = race.status === 'completed';
          const isUpcoming = race.status === 'upcoming';

          return (
            <button
              key={race.race_number}
              onClick={() => onRaceSelect?.(race.race_number)}
              disabled={isUpcoming}
              className={cn(
                'flex flex-col items-center p-2 rounded-lg transition-all min-w-[60px]',
                'hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-50',
                isCurrent && 'bg-primary/10 ring-2 ring-primary',
                isCompleted && !isCurrent && 'bg-muted/30'
              )}
            >
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                  isCurrent && 'bg-primary text-primary-foreground',
                  isCompleted && !isCurrent && 'bg-green-500 text-white',
                  isUpcoming && 'bg-muted text-muted-foreground'
                )}
              >
                {race.race_number}
              </div>
              <span
                className={cn(
                  'text-xs mt-1 text-center truncate max-w-[60px]',
                  isCurrent ? 'text-primary font-medium' : 'text-muted-foreground'
                )}
                title={race.name}
              >
                {race.venue.split(' ')[0]}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
