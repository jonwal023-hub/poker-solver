import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../services/api";

interface HandSummary {
  hand_id: string;
  hero_cards: string;
  result_bb: number;
  pot_size: number;
  timestamp: string;
}

export default function SessionsPage() {
  const demoSessionId = "00000000-0000-0000-0000-000000000000";

  const { data, isLoading, error } = useQuery<HandSummary[]>({
    queryKey: ["hands", demoSessionId],
    queryFn: async () => (await api.get(`/sessions/${demoSessionId}/hands`)).data,
  });

  if (isLoading) return <p>Loading hands…</p>;
  if (error) return <p>Could not load hands. Is the backend running?</p>;

  return (
    <div>
      <h1>Recent Hands</h1>
      <table width="100%">
        <thead>
          <tr><th align="left">Hero</th><th align="left">Result (bb)</th><th align="left">Pot</th><th /></tr>
        </thead>
        <tbody>
          {data?.map((h) => (
            <tr key={h.hand_id}>
              <td>{h.hero_cards}</td>
              <td>{h.result_bb.toFixed(1)}</td>
              <td>{h.pot_size.toFixed(1)}</td>
              <td><Link to={`/hands/${h.hand_id}`}>Review</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
