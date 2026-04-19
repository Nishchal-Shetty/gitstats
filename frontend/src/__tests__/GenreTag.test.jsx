import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import GenreTag from "../components/GenreTag";

describe("GenreTag", () => {
  it("renders null when genre is missing", () => {
    const { container } = render(<GenreTag genre={null} confidence={0.9} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders null when genre is "unknown"', () => {
    const { container } = render(<GenreTag genre="unknown" confidence={0.5} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders genre label with underscores replaced by spaces", () => {
    render(<GenreTag genre="web_frontend" confidence={0.85} />);
    expect(screen.getByText("web frontend")).toBeInTheDocument();
  });

  it("renders confidence as percentage", () => {
    render(<GenreTag genre="devtools" confidence={0.73} />);
    expect(screen.getByText("73%")).toBeInTheDocument();
  });

  it("does not render confidence when null", () => {
    render(<GenreTag genre="mobile" confidence={null} />);
    expect(screen.getByText("mobile")).toBeInTheDocument();
    expect(screen.queryByText("%")).toBeNull();
  });

  it("uses fallback colors for unknown genre keys", () => {
    render(<GenreTag genre="some_new_genre" confidence={0.5} />);
    const tag = screen.getByText("some new genre");
    // Fallback bg = #21262d, text = #8b949e
    expect(tag).toHaveStyle({ color: "#8b949e" });
  });
});
