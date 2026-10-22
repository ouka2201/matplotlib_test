


import React from "react";
import dropdown_styles from '../../styles/dropdown.module.css';

interface DropdownProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  isError?: boolean;
}
/**
 * 
 * プルダウン共通
 */
const Dropdown: React.FC<DropdownProps> = ({ options, value, onChange,isError }) => {
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };
  return (

        <select
            className={`${dropdown_styles.dropdown }  
                      ${isError ? dropdown_styles.error_field_select : ''}`}
            value={value}
            onChange={handleChange}
        >
            <option value="">選択してください</option>
            {options.map((option) => (
            <option key={option.value} value={option.value}>
                {option.label}
            </option>
            ))}
        </select>
  );
};

export default Dropdown;

