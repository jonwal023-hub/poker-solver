import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import type { HandReview } from "../types";

export default function HandReviewPage() {
  const { handId } = useParams<{ handId: string }>();

  // Single GET /hands/{id} — backend never re-runs the solver here.
  const { data, isLoading, error } = useQuery<HandReview>({
    queryKey: ["hand", handId],
    queryFn: async () => (await api.get(`/hands/${handId}`)).data,
    enabled: !!handId,
  });

  if (isLoading) return <p>Loading hand…</p>;
  if (error || !data) return <p>Hand not found.</p>;

  return (
    <div>
      <h1>{data.hero_cards} on {data.board_cards ?? "preflop"}</h1>
      <p>Position: {data.position} · Pot: {data.pot_size}bb · Result: {data.result_bb}bb</p>

      <h3>Action sequence</h3>
      <ol>
        {data.action_sequence?.map((a, i) => (
          <li key={i}>{a.street} — {a.player} {a.action}{a.size_bb ? ` ${a.size_bb}bb` : ""}</li>
        ))}
      </ol>

      <h3>Solver analysis (EV loss highlighted)</h3>
      <table width="100%">
        <thead>
          <tr><th align="left">Street</th><th>Recommended</th><th>Actual</th><th>EV loss</th></tr>
        </thead>
        <tbody>
          {data.analysis?.map((a, i) => (
            <tr key={i} style={{ color: a.ev_loss > 0.5 ? "#ff6b6b" : "inherit" }}>
              <td>{a.street}</td>
              <td>{a.recommended}</td>
              <td>{a.actual}</td>
              <td>{a.ev_loss.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
