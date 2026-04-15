import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatCard from "../components/StatCard";

describe("StatCard", () => {
  it("renders title and value", () => {
    render(<StatCard title="Stars" value={1000} average={null} icon="★" />);
    expect(screen.getByText("Stars")).toBeInTheDocument();
    expect(screen.getByText("1,000")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<StatCard title="Forks" value={200} average={null} icon="⑂" />);
    expect(screen.getByText("⑂")).toBeInTheDocument();
  });

  it("shows average when provided", () => {
    render(<StatCard title="Stars" value={5000} average={3000} icon="★" />);
    expect(screen.getByText("avg 3,000")).toBeInTheDocument();
  });

  it("does not show average when null", () => {
    render(<StatCard title="Stars" value={5000} average={null} icon="★" />);
    expect(screen.queryByText(/avg/)).toBeNull();
  });

  it('shows "—" when value is null', () => {
    render(<StatCard title="Stars" value={null} average={null} icon="★" />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("uses green color when value >= average", () => {
    const { container } = render(
      <StatCard title="Stars" value={5000} average={3000} icon="★" />
    );
    const valueEl = container.querySelector(".text-2xl");
    expect(valueEl).toHaveStyle({ color: "#56d364" });
  });

  it("uses yellow color when value is within 20% below average", () => {
    const { container } = render(
      <StatCard title="Stars" value={850} average={1000} icon="★" />
    );
    const valueEl = container.querySelector(".text-2xl");
    expect(valueEl).toHaveStyle({ color: "#e3b341" });
  });

  it("uses red color when value is far below average", () => {
    const { container } = render(
      <StatCard title="Stars" value={100} average={1000} icon="★" />
    );
    const valueEl = container.querySelector(".text-2xl");
    expect(valueEl).toHaveStyle({ color: "#ff7b72" });
  });
});
