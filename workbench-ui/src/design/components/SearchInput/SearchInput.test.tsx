import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { SearchInput } from "./SearchInput";

function TestSearchInput() {
  const [value, setValue] = useState("");
  return (
    <SearchInput
      placeholder="Search turns..."
      value={value}
      onChange={setValue}
    />
  );
}

describe("SearchInput", () => {
  it("renders an input with placeholder", () => {
    render(<TestSearchInput />);
    expect(screen.getByPlaceholderText("Search turns...")).toBeInTheDocument();
  });

  it("has aria-label matching placeholder", () => {
    render(<TestSearchInput />);
    expect(screen.getByLabelText("Search turns...")).toBeInTheDocument();
  });

  it("shows shortcut hint when empty", () => {
    render(<TestSearchInput />);
    expect(screen.getByText("/")).toBeInTheDocument();
  });

  it("focuses input on shortcut key press", () => {
    render(<TestSearchInput />);
    const input = screen.getByLabelText("Search turns...");
    fireEvent.keyDown(window, { key: "/" });
    expect(document.activeElement).toBe(input);
  });

  it("does not focus when typing in another input", () => {
    render(
      <>
        <input data-testid="other-input" />
        <TestSearchInput />
      </>,
    );
    const other = screen.getByTestId("other-input");
    other.focus();
    fireEvent.keyDown(other, { key: "/" });
    expect(document.activeElement).toBe(other);
  });

  it("shows clear button when value is non-empty", () => {
    render(
      <SearchInput
        placeholder="Search"
        value="hello"
        onChange={() => {}}
      />,
    );
    expect(screen.getByLabelText("Clear search")).toBeInTheDocument();
  });

  it("does not show clear button when value is empty", () => {
    render(<TestSearchInput />);
    expect(screen.queryByLabelText("Clear search")).toBeNull();
  });

  it("clears value on clear button click", () => {
    const onChange = vi.fn();
    render(
      <SearchInput
        placeholder="Search"
        value="hello"
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText("Clear search"));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("uses custom shortcut key", () => {
    render(
      <SearchInput
        placeholder="Search"
        value=""
        onChange={() => {}}
        shortcut="s"
      />,
    );
    expect(screen.getByText("s")).toBeInTheDocument();
  });
});
