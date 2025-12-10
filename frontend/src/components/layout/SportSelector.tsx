import { useSports } from '@/hooks';
import { Select } from '@/components/ui/select';
import { useState } from 'react';

interface SportSelectorProps {
  value?: number;
  onChange?: (sportId: number | undefined) => void;
}

export function SportSelector({ value, onChange }: SportSelectorProps) {
  const { data: sports = [], isLoading } = useSports();
  const [selectedSport, setSelectedSport] = useState<number | undefined>(value);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const sportId = e.target.value ? parseInt(e.target.value, 10) : undefined;
    setSelectedSport(sportId);
    onChange?.(sportId);
  };

  return (
    <Select
      value={selectedSport?.toString() || ''}
      onChange={handleChange}
      disabled={isLoading}
    >
      <option value="">All Sports</option>
      {sports.map((sport) => (
        <option key={sport.id} value={sport.id}>
          {sport.name}
        </option>
      ))}
    </Select>
  );
}

