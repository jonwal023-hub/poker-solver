import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import type { OpponentProfile } from "../types";

export default function OpponentPage() {
  const { opponentId } = useParams<{ opponentId: string }>();

  const { data, isLoading, error } = useQuery<OpponentProfile>({
    queryKey: ["opponent", opponentId],
    queryFn: async () => (await api.get(`/opponents/${opponentId}`)).data,
    enabled: !!opponentId,
  });

  if (isLoading) return <p>Loading opponent profile…</p>;
  if (error || !data) return <p>No profile cached for this opponent yet.</p>;

  return (
    <div>
      <h1>{data.screen_name} <span style={{ opacity: 0.6 }}>({data.tier})</span></h1>
      <p>Hands seen: {data.hands_seen}</p>
      <ul>
        <li>VPIP: {(data.vpip * 100).toFixed(1)}%</li>
        <li>PFR: {(data.pfr * 100).toFixed(1)}%</li>
        <li>Aggression: {(data.aggression * 100).toFixed(1)}%</li>
        <li>River bluff freq: {(data.river_bluff_freq * 100).toFixed(1)}%</li>
        <li>Fold to cbet: {(data.fold_to_cbet * 100).toFixed(1)}%</li>
      </ul>
      <h3>Jam/call adjustment ({data.tier})</h3>
      <p>Widen call-jam range by {(data.jam_call_strategy.call_jam_widen * 100).toFixed(0)}%, bluff-jam freq {(data.jam_call_strategy.jam_bluff_freq * 100).toFixed(0)}%</p>
    </div>
  );
}
