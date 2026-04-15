import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("No authorization code received from GitHub.");
      return;
    }

    login(code)
      .then(() => navigate("/", { replace: true }))
      .catch((err) => {
        console.error("Auth failed:", err);
        setError(err.response?.data?.detail || "Authentication failed. Please try again.");
      });
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="text-red-400 text-sm">{error}</div>
        <button
          onClick={() => navigate("/")}
          className="text-indigo-400 text-sm hover:underline"
        >
          ← Back to home
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      <div className="text-gray-400 text-sm">Signing you in…</div>
    </div>
  );
}
