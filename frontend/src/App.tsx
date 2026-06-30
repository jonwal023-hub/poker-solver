import { Routes, Route, Link } from "react-router-dom";
import SessionsPage from "./pages/SessionsPage";
import HandReviewPage from "./pages/HandReviewPage";
import OpponentPage from "./pages/OpponentPage";

export default function App() {
  return (
    <div className="container">
      <nav style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <Link to="/">Sessions</Link>
        <Link to="/opponents/demo">Opponents</Link>
      </nav>
      <Routes>
        <Route path="/" element={<SessionsPage />} />
        <Route path="/hands/:handId" element={<HandReviewPage />} />
        <Route path="/opponents/:opponentId" element={<OpponentPage />} />
      </Routes>
    </div>
  );
}
