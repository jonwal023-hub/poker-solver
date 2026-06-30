export type Street = "PREFLOP" | "FLOP" | "TURN" | "RIVER";

export interface HandActionOut {
  street: Street;
  player: string;
  action: "FOLD" | "CHECK" | "CALL" | "BET" | "RAISE" | "ALL_IN";
  size_bb: number | null;
  order: number;
}

export interface SolverAnalysisOut {
  street: Street;
  recommended: string;
  actual: string;
  ev_recommended: number;
  ev_actual: number;
  ev_loss: number;
  solver_version: string;
}

export interface DecisionSnapshotOut {
  street: Street;
  state_hash: string;
  spr: number;
  board_texture: string | null;
  hero_features: Record<string, unknown>;
  villain_features: Record<string, unknown>;
}

export interface HandReview {
  hand_id: string;
  hero_cards: string;
  board_cards: string | null;
  position: string;
  result_bb: number;
  pot_size: number;
  showdown: boolean;
  timestamp: string;
  action_sequence: HandActionOut[] | null;
  analysis: SolverAnalysisOut[] | null;
  snapshots: DecisionSnapshotOut[] | null;
}

export interface OpponentProfile {
  opponent_id: string;
  screen_name: string;
  hands_seen: number;
  vpip: number;
  pfr: number;
  aggression: number;
  river_bluff_freq: number;
  fold_to_cbet: number;
  tier: "NIT" | "TAG" | "LAG" | "MANIAC";
  jam_call_strategy: { call_jam_widen: number; jam_bluff_freq: number };
}
