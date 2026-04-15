import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock AuthContext
const mockLogin = vi.fn();
vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    login: mockLogin,
  }),
}));

import AuthCallback from "../pages/AuthCallback";

function renderWithRouter(searchParams = "") {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback${searchParams}`]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("AuthCallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows error when no code param is present", async () => {
    renderWithRouter();
    await waitFor(() => {
      expect(
        screen.getByText("No authorization code received from GitHub.")
      ).toBeInTheDocument();
    });
  });

  it("shows spinner while logging in", () => {
    // login never resolves so spinner stays
    mockLogin.mockReturnValue(new Promise(() => {}));
    renderWithRouter("?code=test123");
    expect(screen.getByText(/Signing you in/)).toBeInTheDocument();
  });

  it("navigates to home on successful login", async () => {
    mockLogin.mockResolvedValue({ username: "testuser" });
    renderWithRouter("?code=good-code");

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("good-code");
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("shows error message on login failure", async () => {
    mockLogin.mockRejectedValue({
      response: { data: { detail: "OAuth token expired" } },
    });
    renderWithRouter("?code=bad-code");

    await waitFor(() => {
      expect(screen.getByText("OAuth token expired")).toBeInTheDocument();
    });
  });
});
