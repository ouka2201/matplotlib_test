import Dropdown from "./dropdown"

const App = () => {
  const options = [
    { value: "apple", label: "Apple" },
    { value: "banana", label: "Banana" },
    { value: "cherry", label: "Cherry" },
  ];

  const handleDropdownChange = (value) => {
    console.log("Selected value:", value); // 選択された値をコンソールに表示
  };

  return (
    <div>
      <h1>Fruit Selector</h1>
      <Dropdown
        label="Choose a fruit"
        options={options}
        placeholder="Select a fruit"
        onChange={handleDropdownChange}
      />
    </div>
  );
};

export default App;