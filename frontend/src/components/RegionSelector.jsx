import React from 'react';
interface RegionSelectorProps {
  value: number;
  onChange: (year: number) => void;
}
const currentYear = new Date().getFullYear();
const years = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i);
const RegionSelector: React.FC<RegionSelectorProps> = ({ value, onChange }) => {
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="bg-secondary text-foreground border border-border rounded-md px-3 py-2 text-sm font-mono-data focus:outline-none focus:ring-1 focus:ring-ring appearance-none cursor-pointer"
    >
      {years.map((y) => (
        <option key={y} value={y}>
          {y}
        </option>
      ))}
    </select>
  );
};
export default RegionSelector;
